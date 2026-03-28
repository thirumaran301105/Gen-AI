"""
Advanced ML Model Manager with Ensemble Support
Handles multiple model architectures, versioning, and predictions
"""

import os
import json
import logging
from typing import Dict, List, Tuple, Optional
from pathlib import Path
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from datetime import datetime
import numpy as np
import cv2
from functools import lru_cache
import pickle

try:
    import tensorflow as tf
    from tensorflow.keras.applications import MobileNetV2, EfficientNetB4, ResNet50
    from tensorflow.keras.preprocessing import image as keras_image
except ImportError:
    print("⚠️  TensorFlow not installed. Install for full functionality.")

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class PredictionResult:
    """Structured prediction result"""
    disease_id: str
    disease_name: str
    confidence: float
    model_name: str
    processing_time: float
    image_shape: Tuple
    ensemble_results: Optional[Dict] = None
    model_version: str = "2.0"

class BaseModelWrapper(ABC):
    """Abstract base class for model wrappers"""
    
    def __init__(self, model_name: str, model_path: str):
        self.model_name = model_name
        self.model_path = model_path
        self.model = None
        self.classes = []
        self.input_shape = (224, 224, 3)
        self.load_model()
    
    @abstractmethod
    def load_model(self):
        """Load model from disk"""
        pass
    
    @abstractmethod
    def preprocess(self, image: np.ndarray) -> np.ndarray:
        """Preprocess image for model input"""
        pass
    
    @abstractmethod
    def predict(self, image: np.ndarray) -> Tuple[str, float]:
        """Make prediction on image"""
        pass
    
    def unload_model(self):
        """Free up memory"""
        if self.model:
            del self.model
            self.model = None

class MobileNetV2Wrapper(BaseModelWrapper):
    """MobileNetV2 Model Wrapper"""
    
    def __init__(self, model_path: str):
        super().__init__("MobileNetV2", model_path)
    
    def load_model(self):
        """Load pretrained MobileNetV2"""
        try:
            if os.path.exists(self.model_path):
                self.model = tf.keras.models.load_model(self.model_path)
                logger.info(f"✅ Loaded {self.model_name} from {self.model_path}")
            else:
                logger.warning(f"⚠️  Model not found at {self.model_path}")
                self.model = None
        except Exception as e:
            logger.error(f"❌ Failed to load {self.model_name}: {e}")
            self.model = None
    
    def preprocess(self, image: np.ndarray) -> np.ndarray:
        """Preprocess image for MobileNetV2"""
        # Resize
        img = cv2.resize(image, (224, 224))
        
        # Normalize to [0, 1]
        if img.max() > 1:
            img = img / 255.0
        
        # Add batch dimension
        img = np.expand_dims(img, axis=0)
        
        return img
    
    def predict(self, image: np.ndarray) -> Tuple[str, float]:
        """Predict disease from image"""
        if self.model is None:
            return "Unknown", 0.0
        
        try:
            preprocessed = self.preprocess(image)
            predictions = self.model.predict(preprocessed, verbose=0)
            
            class_id = np.argmax(predictions[0])
            confidence = float(np.max(predictions[0]))
            
            # Get class name from model metadata if available
            class_name = self.classes[class_id] if self.classes else f"Class_{class_id}"
            
            return class_name, confidence
        except Exception as e:
            logger.error(f"Prediction error: {e}")
            return "Error", 0.0

class EfficientNetWrapper(BaseModelWrapper):
    """EfficientNet Model Wrapper"""
    
    def __init__(self, model_path: str):
        super().__init__("EfficientNet", model_path)
        self.input_shape = (380, 380, 3)
    
    def load_model(self):
        """Load EfficientNet model"""
        try:
            if os.path.exists(self.model_path):
                self.model = tf.keras.models.load_model(self.model_path)
                logger.info(f"✅ Loaded {self.model_name}")
            else:
                logger.warning(f"⚠️  {self.model_name} not found")
        except Exception as e:
            logger.error(f"Failed to load {self.model_name}: {e}")
    
    def preprocess(self, image: np.ndarray) -> np.ndarray:
        """Preprocess for EfficientNet"""
        img = cv2.resize(image, self.input_shape[:2])
        
        if img.max() > 1:
            img = img / 255.0
        
        img = np.expand_dims(img, axis=0)
        return img
    
    def predict(self, image: np.ndarray) -> Tuple[str, float]:
        """Predict using EfficientNet"""
        if self.model is None:
            return "Unknown", 0.0
        
        try:
            preprocessed = self.preprocess(image)
            predictions = self.model.predict(preprocessed, verbose=0)
            
            class_id = np.argmax(predictions[0])
            confidence = float(np.max(predictions[0]))
            class_name = self.classes[class_id] if self.classes else f"Class_{class_id}"
            
            return class_name, confidence
        except Exception as e:
            logger.error(f"EfficientNet prediction error: {e}")
            return "Error", 0.0

class ResNet50Wrapper(BaseModelWrapper):
    """ResNet50 Model Wrapper"""
    
    def __init__(self, model_path: str):
        super().__init__("ResNet50", model_path)
    
    def load_model(self):
        """Load ResNet50 model"""
        try:
            if os.path.exists(self.model_path):
                self.model = tf.keras.models.load_model(self.model_path)
                logger.info(f"✅ Loaded {self.model_name}")
            else:
                logger.warning(f"⚠️  {self.model_name} not found")
        except Exception as e:
            logger.error(f"Failed to load {self.model_name}: {e}")
    
    def preprocess(self, image: np.ndarray) -> np.ndarray:
        """Preprocess for ResNet50"""
        img = cv2.resize(image, (224, 224))
        
        if img.max() > 1:
            img = img / 255.0
        
        img = np.expand_dims(img, axis=0)
        return img
    
    def predict(self, image: np.ndarray) -> Tuple[str, float]:
        """Predict using ResNet50"""
        if self.model is None:
            return "Unknown", 0.0
        
        try:
            preprocessed = self.preprocess(image)
            predictions = self.model.predict(preprocessed, verbose=0)
            
            class_id = np.argmax(predictions[0])
            confidence = float(np.max(predictions[0]))
            class_name = self.classes[class_id] if self.classes else f"Class_{class_id}"
            
            return class_name, confidence
        except Exception as e:
            logger.error(f"ResNet50 prediction error: {e}")
            return "Error", 0.0

class EnsembleModelManager:
    """Manages multiple models for ensemble predictions"""
    
    def __init__(self, model_dir: str = "models", use_ensemble: bool = True):
        self.model_dir = model_dir
        self.use_ensemble = use_ensemble
        self.models: Dict[str, BaseModelWrapper] = {}
        self.classes = []
        self.model_metadata = {}
        
        os.makedirs(model_dir, exist_ok=True)
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize all available models"""
        logger.info("Initializing models...")
        
        # Paths
        mobilenet_path = os.path.join(self.model_dir, "mobilenetv2_model.h5")
        efficientnet_path = os.path.join(self.model_dir, "efficientnet_model.h5")
        resnet_path = os.path.join(self.model_dir, "resnet50_model.h5")
        
        # Load models
        self.models["mobilenetv2"] = MobileNetV2Wrapper(mobilenet_path)
        
        if self.use_ensemble:
            self.models["efficientnet"] = EfficientNetWrapper(efficientnet_path)
            self.models["resnet50"] = ResNet50Wrapper(resnet_path)
        
        # Set class names
        self._load_class_names()
        
        logger.info(f"✅ Models initialized: {list(self.models.keys())}")
    
    def _load_class_names(self):
        """Load disease class names"""
        metadata_path = os.path.join(self.model_dir, "metadata.json")
        
        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                    self.classes = metadata.get('classes', ['Early_Blight', 'Healthy', 'Late_Blight'])
                    self.model_metadata = metadata
            except Exception as e:
                logger.warning(f"Could not load metadata: {e}")
                self.classes = ['Early_Blight', 'Healthy', 'Late_Blight']
        else:
            self.classes = ['Early_Blight', 'Healthy', 'Late_Blight']
        
        # Set classes for all models
        for model in self.models.values():
            model.classes = self.classes
    
    def predict_single(self, image: np.ndarray, model_name: str = "mobilenetv2") -> PredictionResult:
        """Make single model prediction"""
        import time
        start_time = time.time()
        
        if model_name not in self.models:
            logger.error(f"Model {model_name} not found")
            return PredictionResult(
                disease_id="unknown",
                disease_name="Unknown",
                confidence=0.0,
                model_name=model_name,
                processing_time=0.0,
                image_shape=image.shape
            )
        
        model = self.models[model_name]
        disease_name, confidence = model.predict(image)
        
        # Get disease ID
        disease_id = disease_name.lower().replace(" ", "_")
        
        processing_time = time.time() - start_time
        
        return PredictionResult(
            disease_id=disease_id,
            disease_name=disease_name,
            confidence=confidence,
            model_name=model_name,
            processing_time=processing_time,
            image_shape=image.shape
        )
    
    def predict_ensemble(self, image: np.ndarray) -> PredictionResult:
        """Make ensemble prediction (average of multiple models)"""
        import time
        start_time = time.time()
        
        if not self.use_ensemble or len(self.models) < 2:
            return self.predict_single(image)
        
        predictions = {}
        ensemble_results = {}
        
        # Get predictions from all models
        for model_name in self.models:
            try:
                disease_name, confidence = self.models[model_name].predict(image)
                predictions[disease_name] = predictions.get(disease_name, 0) + confidence
                ensemble_results[model_name] = {
                    "disease": disease_name,
                    "confidence": float(confidence)
                }
            except Exception as e:
                logger.error(f"Error in {model_name}: {e}")
        
        # Average predictions
        if predictions:
            avg_disease = max(predictions, key=predictions.get)
            avg_confidence = predictions[avg_disease] / len(self.models)
        else:
            avg_disease = "Unknown"
            avg_confidence = 0.0
        
        disease_id = avg_disease.lower().replace(" ", "_")
        processing_time = time.time() - start_time
        
        return PredictionResult(
            disease_id=disease_id,
            disease_name=avg_disease,
            confidence=min(avg_confidence, 1.0),
            model_name="ensemble",
            processing_time=processing_time,
            image_shape=image.shape,
            ensemble_results=ensemble_results
        )
    
    def predict(self, image: np.ndarray, use_ensemble: bool = None) -> PredictionResult:
        """Make prediction with automatic model selection"""
        if use_ensemble is None:
            use_ensemble = self.use_ensemble
        
        if use_ensemble and len(self.models) > 1:
            return self.predict_ensemble(image)
        else:
            return self.predict_single(image, "mobilenetv2")
    
    def get_model_info(self) -> Dict:
        """Get information about loaded models"""
        info = {
            "total_models": len(self.models),
            "ensemble_enabled": self.use_ensemble,
            "models": {},
            "classes": self.classes,
            "metadata": self.model_metadata
        }
        
        for name, model in self.models.items():
            info["models"][name] = {
                "name": model.model_name,
                "loaded": model.model is not None,
                "input_shape": model.input_shape,
                "classes": len(model.classes)
            }
        
        return info
    
    def unload_all_models(self):
        """Free up GPU/CPU memory"""
        for model in self.models.values():
            model.unload_model()
        logger.info("All models unloaded")

# Global instance for singleton pattern
_model_manager = None

def get_model_manager(model_dir: str = "models", use_ensemble: bool = True) -> EnsembleModelManager:
    """Get or create model manager instance"""
    global _model_manager
    if _model_manager is None:
        _model_manager = EnsembleModelManager(model_dir, use_ensemble)
    return _model_manager

if __name__ == "__main__":
    # Test
    manager = get_model_manager()
    print(json.dumps(manager.get_model_info(), indent=2))
