

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, joinedload
from . import models, database
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
import re

models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="GearGuard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- SCHEMAS ---
class RequestCreate(BaseModel):
    subject: str
    request_type: str 
    equipment_id: Optional[int] = None
    work_center_id: Optional[int] = None
    scheduled_date: Optional[datetime] = None
    priority: int = 1
    
    # --- ADDED THESE FIELDS TO MATCH YOUR FORM ---
    technician_id: Optional[int] = None
    team_id: Optional[int] = None  # User selected team
    duration: Optional[float] = 0.0
    created_by_id: Optional[int] = None

# --- UPDATE THE SCHEMA ---
class RequestUpdate(BaseModel):
    stage: Optional[str] = None
    duration_hours: Optional[float] = None
    technician_id: Optional[int] = None
    priority: Optional[int] = None
    # --- ADD THESE ---
    notes: Optional[str] = None
    instructions: Optional[str] = None
    worksheet_log: Optional[str] = None
    kanban_state: Optional[str] = None

class EquipmentSchema(BaseModel):
    name: str
    serial_number: str
    category: str
    department: str
    location: str
    maintenance_team_id: int
    technician_id: Optional[int] = None

# --- ENDPOINTS ---


# --- AUTH SCHEMAS ---
class UserLogin(BaseModel):
    email: str
    password: str

class UserSignup(BaseModel):
    name: str
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    user_type: str

    class Config:
        orm_mode = True
        
        
# --- NEW SCHEMAS FOR TEAMS & WORK CENTERS ---

class TeamCreate(BaseModel):
    name: str

class TeamUpdate(BaseModel):
    name: Optional[str] = None
    member_ids: Optional[List[int]] = None # This handles adding/removing members

class WorkCenterCreate(BaseModel):
    name: str
    code: str
    cost_per_hour: float
    capacity: float
    oee_target: float

class WorkCenterUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    cost_per_hour: Optional[float] = None
    capacity: Optional[float] = None
    oee_target: Optional[float] = None
        

def validate_password_strength(password: str) -> bool:
    if len(password) <= 8: return False
    if not re.search(r"[a-z]", password): return False
    if not re.search(r"[A-Z]", password): return False
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password): return False
    return True

@app.post("/login", response_model=UserResponse)
def login(user_data: UserLogin, db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.email == user_data.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Account not exist")
    
    if user.password_hash != user_data.password:
        raise HTTPException(status_code=401, detail="Invalid Password")
        
    return user

@app.post("/signup", status_code=201)
def signup(user_data: UserSignup, db: Session = Depends(database.get_db)):
    existing_user = db.query(models.User).filter(models.User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=409, detail="Email Id should not be a duplicate in database")
    
    if not validate_password_strength(user_data.password):
        raise HTTPException(
            status_code=400, 
            detail="Password must contain a small case, a large case, a special character and length should be in more then 8 charachters."
        )

    new_user = models.User(
        name=user_data.name,
        email=user_data.email,
        password_hash=user_data.password,
        user_type="portal"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "Account created successfully"}

@app.get("/requests/")
def read_requests(db: Session = Depends(database.get_db)):
    return db.query(models.MaintenanceRequest).options(
        joinedload(models.MaintenanceRequest.equipment),
        joinedload(models.MaintenanceRequest.work_center),
        joinedload(models.MaintenanceRequest.team),
        joinedload(models.MaintenanceRequest.technician),
        joinedload(models.MaintenanceRequest.created_by)
    ).all()

@app.get("/equipment/")
def read_equipment(db: Session = Depends(database.get_db)):
    return db.query(models.Equipment).options(
        joinedload(models.Equipment.maintenance_team),
        joinedload(models.Equipment.technician)
    ).all()

@app.get("/work-centers/")
def read_work_centers(db: Session = Depends(database.get_db)):
    return db.query(models.WorkCenter).all()

@app.get("/teams/")
def read_teams(db: Session = Depends(database.get_db)):
    return db.query(models.MaintenanceTeam).options(joinedload(models.MaintenanceTeam.members)).all()

@app.get("/users/")
def read_users(db: Session = Depends(database.get_db)):
    return db.query(models.User).all()

@app.post("/requests/")
def create_request(request: RequestCreate, db: Session = Depends(database.get_db)):
    # 1. Determine Team: Use User Selection -> Fallback to Equipment Default -> None
    final_team_id = request.team_id
    
    if not final_team_id and request.equipment_id:
        # If user didn't select a team, try to auto-fill from Equipment
        equipment = db.query(models.Equipment).filter(models.Equipment.id == request.equipment_id).first()
        if equipment:
            final_team_id = equipment.maintenance_team_id
            
    try:
        req_type_enum = models.RequestType(request.request_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid type")

    new_req = models.MaintenanceRequest(
        subject=request.subject,
        request_type=req_type_enum,
        equipment_id=request.equipment_id,
        work_center_id=request.work_center_id,
        assigned_team_id=final_team_id, # Use the calculated ID
        technician_id=request.technician_id, # Save the Technician
        scheduled_date=request.scheduled_date,
        duration_hours=request.duration, # Save the duration
        stage=models.RequestStage.NEW,
        priority=request.priority,
        created_by_id=request.created_by_id
    )
    
    db.add(new_req)
    db.commit()
    db.refresh(new_req)
    return new_req

@app.put("/requests/{request_id}/stage")
def update_stage(request_id: int, update_data: RequestUpdate, db: Session = Depends(database.get_db)):
    req = db.query(models.MaintenanceRequest).filter(models.MaintenanceRequest.id == request_id).first()
    if not req: raise HTTPException(404, "Not found")
    
    # Update fields if they are provided
    if update_data.stage: req.stage = update_data.stage
    if update_data.duration_hours is not None: req.duration_hours = update_data.duration_hours
    if update_data.technician_id: req.technician_id = update_data.technician_id
    if update_data.priority: req.priority = update_data.priority
    if update_data.kanban_state: req.kanban_state = update_data.kanban_state # <--- SAVE IT
    
    # --- SAVE NEW FIELDS ---
    if update_data.notes is not None: req.notes = update_data.notes
    if update_data.instructions is not None: req.instructions = update_data.instructions
    if update_data.worksheet_log is not None: req.worksheet_log = update_data.worksheet_log
    # -----------------------

    # Scrap Logic
    if req.stage == models.RequestStage.SCRAP and req.equipment_id:
        equipment = db.query(models.Equipment).filter(models.Equipment.id == req.equipment_id).first()
        if equipment: equipment.is_active = False 
    
    db.commit()
    db.refresh(req) # Refresh to get updated data back
    return req

# CRUD for Equipment
@app.post("/equipment/")
def create_equipment(equip: EquipmentSchema, db: Session = Depends(database.get_db)):
    new_equip = models.Equipment(**equip.dict(), is_active=True)
    db.add(new_equip)
    db.commit()
    db.refresh(new_equip)
    return new_equip

@app.delete("/equipment/{equipment_id}")
def delete_equipment(equipment_id: int, db: Session = Depends(database.get_db)):
    db.query(models.Equipment).filter(models.Equipment.id == equipment_id).delete()
    db.commit()
    return {"msg": "Deleted"}

@app.put("/equipment/{equipment_id}")
def update_equipment(equipment_id: int, equip: EquipmentSchema, db: Session = Depends(database.get_db)):
    db_equip = db.query(models.Equipment).filter(models.Equipment.id == equipment_id).first()
    if not db_equip:
        raise HTTPException(status_code=404, detail="Equipment not found")
    
    db_equip.name = equip.name
    db_equip.serial_number = equip.serial_number
    db_equip.category = equip.category
    db_equip.department = equip.department
    db_equip.location = equip.location
    db_equip.maintenance_team_id = equip.maintenance_team_id
    db_equip.technician_id = equip.technician_id
    
    db.commit()
    db.refresh(db_equip)
    return db_equip
    
@app.get("/equipment/{equipment_id}/stats")
def get_equipment_stats(equipment_id: int, db: Session = Depends(database.get_db)):
    count = db.query(models.MaintenanceRequest).filter(
        models.MaintenanceRequest.equipment_id == equipment_id,
        models.MaintenanceRequest.stage != models.RequestStage.REPAIRED,
        models.MaintenanceRequest.stage != models.RequestStage.SCRAP
    ).count()
    return {"open_requests": count}


# --- TEAMS CRUD ---

@app.post("/teams/", response_model=None)
def create_team(team: TeamCreate, db: Session = Depends(database.get_db)):
    db_team = models.MaintenanceTeam(name=team.name)
    db.add(db_team)
    db.commit()
    db.refresh(db_team)
    return db_team

@app.put("/teams/{team_id}")
def update_team(team_id: int, team_data: TeamUpdate, db: Session = Depends(database.get_db)):
    db_team = db.query(models.MaintenanceTeam).filter(models.MaintenanceTeam.id == team_id).first()
    if not db_team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    if team_data.name:
        db_team.name = team_data.name
        
    # --- LOGIC TO ADD/REMOVE MEMBERS ---
    if team_data.member_ids is not None:
        # 1. Clear existing members (optional: depends if you want to wipe previous list)
        # For a pure "set this list" approach:
        current_members = db.query(models.User).filter(models.User.team_id == team_id).all()
        for member in current_members:
            member.team_id = None # Unassign them first
            
        # 2. Assign new members
        if team_data.member_ids:
            users_to_add = db.query(models.User).filter(models.User.id.in_(team_data.member_ids)).all()
            for user in users_to_add:
                user.team_id = team_id

    db.commit()
    db.refresh(db_team)
    # Return with members loaded so frontend updates immediately
    return db.query(models.MaintenanceTeam).options(joinedload(models.MaintenanceTeam.members)).filter(models.MaintenanceTeam.id == team_id).first()

@app.delete("/teams/{team_id}")
def delete_team(team_id: int, db: Session = Depends(database.get_db)):
    # 1. Check if team exists
    team = db.query(models.MaintenanceTeam).filter(models.MaintenanceTeam.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # 2. Unassign Members (Fixes the ForeignKeyViolation error)
    # We use .update() to set team_id to NULL for all users in this team
    db.query(models.User).filter(models.User.team_id == team_id).update({"team_id": None})

    # 3. Unassign Equipment (Prevent potential future errors)
    # If any equipment is assigned to this team, unassign it too
    db.query(models.Equipment).filter(models.Equipment.maintenance_team_id == team_id).update({"maintenance_team_id": None})
    
    # 4. Unassign Requests (Optional but recommended)
    # If any active requests are assigned to this team, unassign them
    db.query(models.MaintenanceRequest).filter(models.MaintenanceRequest.assigned_team_id == team_id).update({"assigned_team_id": None})

    # 5. Now it is safe to delete the team
    db.query(models.MaintenanceTeam).filter(models.MaintenanceTeam.id == team_id).delete()
    
    db.commit()
    return {"message": "Team deleted successfully"}

# --- WORK CENTERS CRUD ---

@app.post("/work-centers/")
def create_work_center(wc: WorkCenterCreate, db: Session = Depends(database.get_db)):
    new_wc = models.WorkCenter(**wc.dict())
    db.add(new_wc)
    db.commit()
    db.refresh(new_wc)
    return new_wc

@app.put("/work-centers/{wc_id}")
def update_work_center(wc_id: int, wc_data: WorkCenterUpdate, db: Session = Depends(database.get_db)):
    db_wc = db.query(models.WorkCenter).filter(models.WorkCenter.id == wc_id).first()
    if not db_wc:
        raise HTTPException(404, "Work Center not found")
    
    for key, value in wc_data.dict(exclude_unset=True).items():
        setattr(db_wc, key, value)
        
    db.commit()
    db.refresh(db_wc)
    return db_wc

@app.delete("/work-centers/{wc_id}")
def delete_work_center(wc_id: int, db: Session = Depends(database.get_db)):
    db.query(models.WorkCenter).filter(models.WorkCenter.id == wc_id).delete()
    db.commit()
    return {"message": "Work Center deleted"}