"""
Advanced Database Service Layer
Handles all database operations with SQLAlchemy ORM
Supports SQLite, PostgreSQL, and MongoDB
"""

import json
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
import hashlib

from sqlalchemy import create_engine, Column, String, Float, DateTime, Integer, Boolean, JSON, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Base model for all database models
Base = declarative_base()

# ============================================
# DATABASE MODELS
# ============================================

class PredictionRecord(Base):
    """Store all predictions for analytics"""
    __tablename__ = 'predictions'
    
    id = Column(Integer, primary_key=True)
    prediction_id = Column(String(64), unique=True, index=True)
    user_id = Column(String(64), nullable=True)
    
    # Image metadata
    image_hash = Column(String(64), index=True)
    image_size = Column(Integer)
    image_shape = Column(String(50))
    
    # Prediction details
    predicted_disease = Column(String(100), index=True)
    disease_id = Column(String(100), index=True)
    confidence = Column(Float)
    
    # Model information
    model_name = Column(String(50))
    model_version = Column(String(20))
    processing_time = Column(Float)
    
    # Ensemble results
    ensemble_results = Column(JSON, nullable=True)
    
    # Location/context
    location = Column(String(200), nullable=True)
    crop_type = Column(String(100), nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Feedback
    farmer_feedback = Column(String(20), nullable=True)  # correct, incorrect, uncertain
    actual_disease = Column(String(100), nullable=True)
    feedback_received = Column(Boolean, default=False)
    
    def __repr__(self):
        return f"<Prediction(id={self.id}, disease='{self.predicted_disease}', confidence={self.confidence:.2f})>"

class TreatmentHistory(Base):
    """Track treatment recommendations and outcomes"""
    __tablename__ = 'treatment_history'
    
    id = Column(Integer, primary_key=True)
    treatment_id = Column(String(64), unique=True, index=True)
    prediction_id = Column(String(64), index=True)
    user_id = Column(String(64), nullable=True)
    
    disease = Column(String(100), index=True)
    
    # Treatment details
    chemical_treatment = Column(Text)
    organic_treatment = Column(Text)
    dosage = Column(Text)
    application_method = Column(String(200))
    
    # Weather at time of treatment
    weather_conditions = Column(JSON)
    
    # Outcome tracking
    treatment_applied = Column(Boolean, default=False)
    treatment_date = Column(DateTime, nullable=True)
    
    # Result
    crop_outcome = Column(String(50), nullable=True)  # improved, no_change, worsened
    yield_impact = Column(Float, nullable=True)  # percentage
    cost = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class UserProfile(Base):
    """Store user information and preferences"""
    __tablename__ = 'user_profiles'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(64), unique=True, index=True)
    
    # User info
    name = Column(String(200))
    phone = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True)
    
    # Location
    district = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    country = Column(String(100), default="India")
    
    # Farm info
    farm_size_acres = Column(Float, nullable=True)
    primary_crops = Column(JSON)  # List of crops
    
    # Preferences
    language_preference = Column(String(10), default="ta")
    notification_enabled = Column(Boolean, default=True)
    
    # Stats
    total_predictions = Column(Integer, default=0)
    accuracy_feedback = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class WeatherHistory(Base):
    """Store weather data for correlation with diseases"""
    __tablename__ = 'weather_history'
    
    id = Column(Integer, primary_key=True)
    location = Column(String(200), index=True)
    
    temperature = Column(Float)
    humidity = Column(Float)
    rainfall = Column(Float)
    wind_speed = Column(Float)
    weather_condition = Column(String(100))
    
    # Additional metrics
    pressure = Column(Float, nullable=True)
    uv_index = Column(Float, nullable=True)
    
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)

class ModelPerformance(Base):
    """Track model performance metrics"""
    __tablename__ = 'model_performance'
    
    id = Column(Integer, primary_key=True)
    model_name = Column(String(100), index=True)
    model_version = Column(String(50))
    
    # Accuracy metrics
    accuracy = Column(Float)
    precision = Column(Float)
    recall = Column(Float)
    f1_score = Column(Float)
    
    # Performance metrics
    avg_inference_time = Column(Float)
    predictions_count = Column(Integer)
    
    # Calibration
    confidence_calibration = Column(Float)
    
    evaluated_at = Column(DateTime, default=datetime.utcnow)

# ============================================
# DATABASE SERVICE CLASS
# ============================================

class DatabaseService:
    """Database service with connection pooling and transaction management"""
    
    def __init__(self, database_url: str = "sqlite:///./rural_advisory.db", echo: bool = False):
        """
        Initialize database service
        
        Args:
            database_url: Database connection URL
            echo: Enable SQL logging
        """
        self.database_url = database_url
        self.echo = echo
        
        # Create engine with appropriate settings
        if "sqlite" in database_url:
            self.engine = create_engine(
                database_url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
                echo=echo
            )
        else:
            self.engine = create_engine(
                database_url,
                pool_size=20,
                max_overflow=10,
                echo=echo
            )
        
        # Create session factory
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # Create tables
        Base.metadata.create_all(self.engine)
        logger.info("✅ Database initialized")
    
    @contextmanager
    def get_session(self) -> Session:
        """Context manager for database sessions"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            session.close()
    
    # ============================================
    # PREDICTION OPERATIONS
    # ============================================
    
    def save_prediction(self, prediction_data: Dict[str, Any]) -> str:
        """Save prediction record"""
        with self.get_session() as session:
            # Generate prediction ID
            prediction_id = hashlib.md5(
                f"{datetime.utcnow().isoformat()}{prediction_data.get('image_hash', 'unknown')}".encode()
            ).hexdigest()
            
            record = PredictionRecord(
                prediction_id=prediction_id,
                user_id=prediction_data.get('user_id'),
                image_hash=prediction_data.get('image_hash'),
                image_size=prediction_data.get('image_size'),
                image_shape=str(prediction_data.get('image_shape')),
                predicted_disease=prediction_data.get('predicted_disease'),
                disease_id=prediction_data.get('disease_id'),
                confidence=prediction_data.get('confidence'),
                model_name=prediction_data.get('model_name'),
                model_version=prediction_data.get('model_version', '2.0'),
                processing_time=prediction_data.get('processing_time'),
                ensemble_results=prediction_data.get('ensemble_results'),
                location=prediction_data.get('location'),
                crop_type=prediction_data.get('crop_type')
            )
            
            session.add(record)
            session.flush()
            
            return prediction_id
    
    def get_prediction(self, prediction_id: str) -> Optional[PredictionRecord]:
        """Retrieve prediction by ID"""
        with self.get_session() as session:
            return session.query(PredictionRecord).filter_by(prediction_id=prediction_id).first()
    
    def get_user_predictions(self, user_id: str, limit: int = 100) -> List[PredictionRecord]:
        """Get all predictions for a user"""
        with self.get_session() as session:
            return session.query(PredictionRecord)\
                .filter_by(user_id=user_id)\
                .order_by(PredictionRecord.created_at.desc())\
                .limit(limit)\
                .all()
    
    def get_recent_predictions(self, limit: int = 100) -> List[PredictionRecord]:
        """Get recent predictions"""
        with self.get_session() as session:
            return session.query(PredictionRecord)\
                .order_by(PredictionRecord.created_at.desc())\
                .limit(limit)\
                .all()
    
    def save_feedback(self, prediction_id: str, feedback: Dict[str, Any]) -> bool:
        """Save farmer feedback on prediction"""
        with self.get_session() as session:
            record = session.query(PredictionRecord).filter_by(prediction_id=prediction_id).first()
            if record:
                record.farmer_feedback = feedback.get('feedback')
                record.actual_disease = feedback.get('actual_disease')
                record.feedback_received = True
                return True
            return False
    
    # ============================================
    # ANALYTICS OPERATIONS
    # ============================================
    
    def get_prediction_stats(self, days: int = 30) -> Dict[str, Any]:
        """Get prediction statistics for period"""
        with self.get_session() as session:
            from sqlalchemy import func
            from datetime import timedelta
            
            start_date = datetime.utcnow() - timedelta(days=days)
            
            query = session.query(PredictionRecord)\
                .filter(PredictionRecord.created_at >= start_date)
            
            total_predictions = query.count()
            avg_confidence = session.query(func.avg(PredictionRecord.confidence))\
                .filter(PredictionRecord.created_at >= start_date).scalar() or 0
            
            # Disease distribution
            disease_counts = session.query(
                PredictionRecord.predicted_disease,
                func.count(PredictionRecord.id)
            ).filter(PredictionRecord.created_at >= start_date)\
             .group_by(PredictionRecord.predicted_disease).all()
            
            return {
                "total_predictions": total_predictions,
                "average_confidence": float(avg_confidence),
                "disease_distribution": {disease: count for disease, count in disease_counts},
                "period_days": days
            }
    
    def get_disease_trends(self, days: int = 90) -> Dict[str, Any]:
        """Get disease trend analysis"""
        with self.get_session() as session:
            from sqlalchemy import func
            from datetime import timedelta
            
            start_date = datetime.utcnow() - timedelta(days=days)
            
            trends = session.query(
                func.date(PredictionRecord.created_at).label('date'),
                PredictionRecord.predicted_disease,
                func.count(PredictionRecord.id)
            ).filter(PredictionRecord.created_at >= start_date)\
             .group_by(func.date(PredictionRecord.created_at), PredictionRecord.predicted_disease)\
             .all()
            
            return {"trends": [(str(t[0]), t[1], t[2]) for t in trends]}
    
    def get_accuracy_by_disease(self) -> Dict[str, float]:
        """Get prediction accuracy per disease (based on feedback)"""
        with self.get_session() as session:
            from sqlalchemy import func
            
            accuracy = session.query(
                PredictionRecord.predicted_disease,
                func.avg(
                    (PredictionRecord.predicted_disease == PredictionRecord.actual_disease).cast('int')
                )
            ).filter(PredictionRecord.feedback_received == True)\
             .group_by(PredictionRecord.predicted_disease).all()
            
            return {disease: acc for disease, acc in accuracy}
    
    # ============================================
    # USER OPERATIONS
    # ============================================
    
    def create_user(self, user_data: Dict[str, Any]) -> str:
        """Create new user profile"""
        with self.get_session() as session:
            user = UserProfile(**user_data)
            session.add(user)
            session.flush()
            return user.user_id
    
    def get_user(self, user_id: str) -> Optional[UserProfile]:
        """Get user profile"""
        with self.get_session() as session:
            return session.query(UserProfile).filter_by(user_id=user_id).first()
    
    def update_user(self, user_id: str, update_data: Dict[str, Any]) -> bool:
        """Update user profile"""
        with self.get_session() as session:
            user = session.query(UserProfile).filter_by(user_id=user_id).first()
            if user:
                for key, value in update_data.items():
                    if hasattr(user, key):
                        setattr(user, key, value)
                return True
            return False
    
    # ============================================
    # TREATMENT OPERATIONS
    # ============================================
    
    def save_treatment(self, treatment_data: Dict[str, Any]) -> str:
        """Save treatment record"""
        with self.get_session() as session:
            treatment_id = hashlib.md5(
                f"{datetime.utcnow().isoformat()}".encode()
            ).hexdigest()
            
            treatment = TreatmentHistory(
                treatment_id=treatment_id,
                **treatment_data
            )
            session.add(treatment)
            session.flush()
            return treatment_id
    
    def get_treatment_outcomes(self, days: int = 90) -> Dict[str, Any]:
        """Get treatment outcome statistics"""
        with self.get_session() as session:
            from sqlalchemy import func
            from datetime import timedelta
            
            start_date = datetime.utcnow() - timedelta(days=days)
            
            outcomes = session.query(
                TreatmentHistory.crop_outcome,
                func.count(TreatmentHistory.id)
            ).filter(TreatmentHistory.updated_at >= start_date)\
             .group_by(TreatmentHistory.crop_outcome).all()
            
            return {outcome: count for outcome, count in outcomes if outcome}

# Global instance
_db_service = None

def get_database_service(database_url: str = "sqlite:///./rural_advisory.db") -> DatabaseService:
    """Get or create database service instance"""
    global _db_service
    if _db_service is None:
        _db_service = DatabaseService(database_url)
    return _db_service

if __name__ == "__main__":
    db = get_database_service()
    print(json.dumps(db.get_prediction_stats(), indent=2, default=str))
