# backend/models.py
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Float, Enum, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from .database import Base

# --- ENUMS ---
class RequestType(str, enum.Enum):
    CORRECTIVE = "Corrective"
    PREVENTIVE = "Preventive"

class RequestStage(str, enum.Enum):
    NEW = "New"
    IN_PROGRESS = "In Progress"
    REPAIRED = "Repaired"
    SCRAP = "Scrap"

class KanbanState(str, enum.Enum):
    NORMAL = "normal"
    BLOCKED = "blocked"
    DONE = "done"

# --- TABLES ---
class MaintenanceTeam(Base):
    __tablename__ = "teams"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    members = relationship("User", back_populates="team")
    equipment = relationship("Equipment", back_populates="maintenance_team")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    
    # --- AUTH FIELDS ---
    email = Column(String, unique=True, index=True, nullable=True) 
    password_hash = Column(String, nullable=True) 
    user_type = Column(String, default="employee") 
    
    avatar_url = Column(String, nullable=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    team = relationship("MaintenanceTeam", back_populates="members")

class Equipment(Base):
    __tablename__ = "equipment"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    serial_number = Column(String, unique=True)
    category = Column(String) 
    department = Column(String)
    location = Column(String)
    purchase_date = Column(DateTime, default=datetime.utcnow)
    warranty_expiration = Column(DateTime)
    is_active = Column(Boolean, default=True)
    
    maintenance_team_id = Column(Integer, ForeignKey("teams.id"))
    technician_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    maintenance_team = relationship("MaintenanceTeam", back_populates="equipment")
    technician = relationship("User") 
    requests = relationship("MaintenanceRequest", back_populates="equipment")

class WorkCenter(Base):
    __tablename__ = "work_centers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    code = Column(String, unique=True)
    cost_per_hour = Column(Float, default=0.0)
    capacity = Column(Float, default=100.0)
    oee_target = Column(Float, default=85.0)
    
    requests = relationship("MaintenanceRequest", back_populates="work_center")

class MaintenanceRequest(Base):
    __tablename__ = "requests"
    id = Column(Integer, primary_key=True, index=True)
    subject = Column(String)
    request_type = Column(Enum(RequestType))
    stage = Column(Enum(RequestStage), default=RequestStage.NEW)
    priority = Column(Integer, default=1)
    
    scheduled_date = Column(DateTime, nullable=True)
    duration_hours = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    notes = Column(Text, nullable=True) 
    instructions = Column(Text, nullable=True) 
    worksheet_log = Column(Text, nullable=True) 
    kanban_state = Column(Enum(KanbanState), default=KanbanState.NORMAL)

    equipment_id = Column(Integer, ForeignKey("equipment.id"), nullable=True)
    work_center_id = Column(Integer, ForeignKey("work_centers.id"), nullable=True) 
    assigned_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    
    # --- FOREIGN KEYS ---
    technician_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True) # <--- 2nd Foreign Key

    # --- RELATIONSHIPS ---
    equipment = relationship("Equipment", back_populates="requests")
    work_center = relationship("WorkCenter", back_populates="requests")
    team = relationship("MaintenanceTeam")

    # --- FIX: Explicitly define foreign_keys ---
    technician = relationship("User", foreign_keys=[technician_id]) 
    created_by = relationship("User", foreign_keys=[created_by_id])