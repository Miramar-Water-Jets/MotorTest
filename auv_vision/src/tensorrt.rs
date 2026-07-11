use anyhow::{bail, Context, Result};
use half::f16;
use opencv::{
    core::{Mat, Size},
    imgproc,
    prelude::*,
};
use tensorrt_infer::{BindingInfo, CudaBuffer, CudaStream, TrtContext, TrtDataType, TrtEngine};

use crate::{BoundingBox, ClassId, Detection};

const CONFIDENCE_THRESHOLD: f32 = 0.25;

pub struct Yolo26Detector {
    gpu_buffers: Vec<CudaBuffer>,
    context: TrtContext,
    stream: CudaStream,
    _engine: TrtEngine,
    input_index: usize,
    output_index: usize,
    input_width: i32,
    input_height: i32,
    input_type: TrtDataType,
    output_type: TrtDataType,
    output_elements: usize,
}

impl Yolo26Detector {
    pub fn from_engine_file(path: &str) -> Result<Self> {
        let engine = TrtEngine::from_file(path).context("load TensorRT engine")?;
        let bindings = engine.bindings();
        let input_index = find_binding(&bindings, true)?;
        let output_index = find_binding(&bindings, false)?;
        let input = &bindings[input_index];
        let output = &bindings[output_index];
        let [batch, channels, input_height, input_width]: [i32; 4] = input
            .dims
            .as_slice()
            .try_into()
            .context("YOLO26 input must have NCHW dimensions")?;

        if batch != 1 || channels != 3 || input_height <= 0 || input_width <= 0 {
            bail!("YOLO26 input must have static [1, 3, height, width] dimensions");
        }
        if !matches!(input.data_type, TrtDataType::Float | TrtDataType::Half) {
            bail!("YOLO26 input must use FP32 or FP16");
        }
        if !matches!(output.data_type, TrtDataType::Float | TrtDataType::Half) {
            bail!("YOLO26 output must use FP32 or FP16");
        }
        if output.byte_size == 0 || output.byte_size % output.data_type.byte_size() != 0 {
            bail!("YOLO26 output binding has an invalid size");
        }

        let gpu_buffers = bindings
            .iter()
            .map(|binding| CudaBuffer::new(binding.byte_size))
            .collect::<std::result::Result<Vec<_>, _>>()
            .context("allocate TensorRT GPU buffers")?;
        let context = engine.create_context().context("create TensorRT context")?;
        let stream = CudaStream::new().context("create CUDA stream")?;

        Ok(Self {
            gpu_buffers,
            context,
            stream,
            _engine: engine,
            input_index,
            output_index,
            input_width,
            input_height,
            input_type: input.data_type,
            output_type: output.data_type,
            output_elements: output.byte_size / output.data_type.byte_size(),
        })
    }

    pub fn detect(&mut self, frame: &Mat) -> Result<Vec<Detection>> {
        let input = self.preprocess(frame)?;
        self.upload_input(&input)?;

        let mut binding_pointers = self
            .gpu_buffers
            .iter()
            .map(CudaBuffer::as_ptr)
            .collect::<Vec<_>>();
        self.context
            .enqueue(&mut binding_pointers, &self.stream)
            .context("enqueue TensorRT inference")?;

        let output = self.download_output()?;
        self.stream
            .synchronize()
            .context("synchronize CUDA stream")?;
        self.decode_output(&output, frame.cols(), frame.rows())
    }

    fn preprocess(&self, frame: &Mat) -> Result<Vec<f32>> {
        let mut resized = Mat::default();
        imgproc::resize(
            frame,
            &mut resized,
            Size::new(self.input_width, self.input_height),
            0.0,
            0.0,
            imgproc::INTER_LINEAR,
        )?;

        let mut rgb = Mat::default();
        imgproc::cvt_color(&resized, &mut rgb, imgproc::COLOR_BGR2RGB, 0)?;
        if !rgb.is_continuous() {
            rgb = rgb.try_clone()?;
        }

        let pixel_count = (self.input_width * self.input_height) as usize;
        let pixels = rgb.data_bytes()?;
        if pixels.len() != pixel_count * 3 {
            bail!("expected a three-channel camera frame");
        }

        let mut nchw = vec![0.0; pixel_count * 3];
        for (index, pixel) in pixels.chunks_exact(3).enumerate() {
            nchw[index] = f32::from(pixel[0]) / 255.0;
            nchw[pixel_count + index] = f32::from(pixel[1]) / 255.0;
            nchw[(pixel_count * 2) + index] = f32::from(pixel[2]) / 255.0;
        }

        Ok(nchw)
    }

    fn upload_input(&self, input: &[f32]) -> Result<()> {
        match self.input_type {
            TrtDataType::Float => self.gpu_buffers[self.input_index]
                .copy_from_host(bytemuck::cast_slice(input), &self.stream)
                .context("copy FP32 input to GPU"),
            TrtDataType::Half => {
                let input = input.iter().copied().map(f16::from_f32).collect::<Vec<_>>();
                self.gpu_buffers[self.input_index]
                    .copy_from_host(bytemuck::cast_slice(&input), &self.stream)
                    .context("copy FP16 input to GPU")
            }
            _ => unreachable!(),
        }
    }

    fn download_output(&self) -> Result<Vec<f32>> {
        match self.output_type {
            TrtDataType::Float => {
                let mut output = vec![0.0; self.output_elements];
                self.gpu_buffers[self.output_index]
                    .copy_to_host(bytemuck::cast_slice_mut(&mut output), &self.stream)
                    .context("copy FP32 output from GPU")?;
                Ok(output)
            }
            TrtDataType::Half => {
                let mut output = vec![f16::from_f32(0.0); self.output_elements];
                self.gpu_buffers[self.output_index]
                    .copy_to_host(bytemuck::cast_slice_mut(&mut output), &self.stream)
                    .context("copy FP16 output from GPU")?;
                Ok(output.into_iter().map(|value| value.to_f32()).collect())
            }
            _ => unreachable!(),
        }
    }

    fn decode_output(
        &self,
        output: &[f32],
        frame_width: i32,
        frame_height: i32,
    ) -> Result<Vec<Detection>> {
        if output.len() % 6 != 0 {
            bail!("YOLO26 end-to-end output must contain rows of six values");
        }

        let x_scale = frame_width as f32 / self.input_width as f32;
        let y_scale = frame_height as f32 / self.input_height as f32;
        let mut detections = Vec::new();

        for row in output.chunks_exact(6) {
            let [x1, y1, x2, y2, confidence, class_id] =
                [row[0], row[1], row[2], row[3], row[4], row[5]];
            if !confidence.is_finite()
                || confidence < CONFIDENCE_THRESHOLD
                || !class_id.is_finite()
                || class_id < 0.0
            {
                continue;
            }

            let Ok(class_id) = ClassId::try_from(class_id as u32) else {
                continue;
            };

            detections.push(Detection {
                class_id,
                confidence,
                bounding_box: BoundingBox {
                    x1: (x1 * x_scale).clamp(0.0, frame_width as f32),
                    y1: (y1 * y_scale).clamp(0.0, frame_height as f32),
                    x2: (x2 * x_scale).clamp(0.0, frame_width as f32),
                    y2: (y2 * y_scale).clamp(0.0, frame_height as f32),
                },
            });
        }

        Ok(detections)
    }
}

fn find_binding(bindings: &[BindingInfo], is_input: bool) -> Result<usize> {
    let mut matching = bindings
        .iter()
        .enumerate()
        .filter_map(|(index, binding)| (binding.is_input == is_input).then_some(index));

    let Some(index) = matching.next() else {
        if is_input {
            bail!("TensorRT engine has no input binding");
        }
        bail!("TensorRT engine has no output binding");
    };

    if matching.next().is_some() {
        if is_input {
            bail!("YOLO26 engine must have one input binding");
        }
        bail!("YOLO26 engine must have one output binding");
    }

    Ok(index)
}
