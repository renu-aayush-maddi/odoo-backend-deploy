# backend/seed.py
from sqlalchemy.orm import Session
from .database import SessionLocal, engine
from . import models
from datetime import datetime, timedelta

# Create tables (Drop existing to ensure schema update if in dev)
# models.Base.metadata.drop_all(bind=engine) # Uncomment this line if you want to wipe DB and start fresh
models.Base.metadata.create_all(bind=engine)

def seed_data():
    db = SessionLocal()

    # Check if data exists
    if db.query(models.MaintenanceTeam).first():
        print("Data already exists. Skipping seed.")
        return

    print("--- Seeding Teams ---")
    team_mech = models.MaintenanceTeam(name="Mechanics")
    team_elec = models.MaintenanceTeam(name="Electricians")
    team_it = models.MaintenanceTeam(name="IT Support")
    db.add_all([team_mech, team_elec, team_it])
    db.commit()

    print("--- Seeding Users ---")
    u1 = models.User(name="Mitchell Admin", email="admin@example.com", password_hash="Password@123", user_type="manager", team_id=team_mech.id)
    u2 = models.User(name="Marc Demo", email="marc@example.com", password_hash="Password@123", user_type="technician", team_id=team_elec.id)
    u3 = models.User(name="Abigail Peterson", email="abigail@example.com", password_hash="Password@123", user_type="technician", team_id=team_it.id)
    u4 = models.User(name="John Client", email="client@example.com", password_hash="Password@123", user_type="portal", team_id=None)

    db.add_all([u1, u2, u3, u4])
    db.commit()

    print("--- Seeding Work Centers ---")
    wc1 = models.WorkCenter(name="Assembly Line 1", code="WC-001", cost_per_hour=150.0)
    wc2 = models.WorkCenter(name="Drill Station", code="WC-002", cost_per_hour=85.0)
    db.add_all([wc1, wc2])
    db.commit()

    print("--- Seeding Equipment ---")
    eq1 = models.Equipment(name="CNC Machine X1", serial_number="MT/125/22778837", category="Heavy Machinery", department="Production", location="Floor 1", maintenance_team_id=team_mech.id, technician_id=u1.id)
    eq2 = models.Equipment(name="Samsung Monitor", serial_number="MT/122/111", category="Monitors", department="Admin", location="Office 202", maintenance_team_id=team_it.id, technician_id=u3.id)
    eq3 = models.Equipment(name="Generator 5000", serial_number="GEN-5K", category="Power", department="Utility", location="Basement", maintenance_team_id=team_elec.id, technician_id=u2.id)
    db.add_all([eq1, eq2, eq3])
    db.commit()
    
    print("--- Seeding Requests ---")
    req1 = models.MaintenanceRequest(
        subject="Leaking Oil", 
        request_type=models.RequestType.CORRECTIVE,
        equipment_id=eq1.id, 
        assigned_team_id=team_mech.id,
        technician_id=u1.id,  
        created_by_id=u1.id,  # Admin created
        stage=models.RequestStage.IN_PROGRESS,
        priority=3
    )
    
    req2 = models.MaintenanceRequest(
        subject="Monthly Checkup", 
        request_type=models.RequestType.PREVENTIVE,
        equipment_id=eq3.id, 
        assigned_team_id=team_elec.id,
        created_by_id=u1.id,  
        stage=models.RequestStage.NEW,
        scheduled_date=datetime.now() + timedelta(days=5),
        priority=2
    )

    req3 = models.MaintenanceRequest(
        subject="Calibration Error", 
        request_type=models.RequestType.CORRECTIVE,
        work_center_id=wc1.id, 
        assigned_team_id=team_mech.id,
        technician_id=u1.id,
        created_by_id=u4.id,  # Portal user created
        stage=models.RequestStage.NEW,
        priority=1
    )

    db.add_all([req1, req2, req3])
    db.commit()

    print("--- Seeding Complete! ---")
    db.close()

if __name__ == "__main__":
    seed_data()