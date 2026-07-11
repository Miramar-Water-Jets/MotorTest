mod tensorrt;

use std::{
    env, thread,
    time::{Duration, Instant},
};

use anyhow::{bail, Context, Result};
use opencv::{core::Mat, prelude::*, videoio};
use r2r::{std_msgs::msg::Float32MultiArray, QosProfile};
use tensorrt::Yolo26Detector;

const GATE_BBOX_TOPIC: &str = "/auv/camera/bboxes_gate";
const CAMERA_INDEX: i32 = 0;
const FRAME_PERIOD: Duration = Duration::from_millis(1_000 / 3);

#[repr(u32)]
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum ClassId {
    Gate = 0,
}

impl TryFrom<u32> for ClassId {
    type Error = ();

    fn try_from(value: u32) -> Result<Self, Self::Error> {
        match value {
            0 => Ok(Self::Gate),
            _ => Err(()),
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct BoundingBox {
    pub x1: f32,
    pub y1: f32,
    pub x2: f32,
    pub y2: f32,
}

impl BoundingBox {
    pub fn width(self) -> f32 {
        self.x2 - self.x1
    }

    pub fn height(self) -> f32 {
        self.y2 - self.y1
    }

    pub fn center(self) -> (f32, f32) {
        ((self.x1 + self.x2) / 2.0, (self.y1 + self.y2) / 2.0)
    }
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Detection {
    pub class_id: ClassId,
    pub confidence: f32,
    pub bounding_box: BoundingBox,
}

fn gate_message(detection: Detection) -> Float32MultiArray {
    Float32MultiArray {
        layout: Default::default(),
        data: vec![
            detection.bounding_box.x1,
            detection.bounding_box.y1,
            detection.bounding_box.x2,
            detection.bounding_box.y2,
            detection.confidence,
        ],
    }
}

fn main() -> Result<()> {
    let engine_path = env::var("AUV_VISION_ENGINE_PATH")
        .context("AUV_VISION_ENGINE_PATH must point to a TensorRT engine")?;
    let mut detector = Yolo26Detector::from_engine_file(&engine_path)?;

    let context = r2r::Context::create()?;
    let mut node = r2r::Node::create(context, "vision_node", "")?;
    let qos = QosProfile::default().best_effort().keep_last(1);
    let gate_publisher = node.create_publisher::<Float32MultiArray>(GATE_BBOX_TOPIC, qos)?;

    let mut camera = videoio::VideoCapture::new(CAMERA_INDEX, videoio::CAP_ANY)?;
    if !camera.is_opened()? {
        bail!("could not open camera {CAMERA_INDEX}");
    }

    loop {
        let frame_start = Instant::now();
        node.spin_once(Duration::ZERO);

        let mut frame = Mat::default();
        if !camera.read(&mut frame)? || frame.empty() {
            eprintln!("failed to capture a frame");
        } else {
            for detection in detector.detect(&frame)? {
                match detection.class_id {
                    ClassId::Gate => gate_publisher.publish(&gate_message(detection))?,
                }
            }
        }

        thread::sleep(FRAME_PERIOD.saturating_sub(frame_start.elapsed()));
    }
}
