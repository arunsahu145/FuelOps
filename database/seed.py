"""
Petrol Pump Finance Manager ERP — Database Seeder
Seeds the database with default admin user, fuel types, nozzles, and tank stock.
"""
import bcrypt
from sqlalchemy.orm import Session
from database.engine import SessionLocal
from database.models import AdminUser, FuelType, Nozzle, TankStock
from config import (
    DEFAULT_ADMIN_USERNAME, DEFAULT_ADMIN_PASSWORD,
    FUEL_TYPES, TOTAL_NOZZLES
)


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def seed_admin(db: Session):
    """Create default admin user if not exists."""
    existing = db.query(AdminUser).filter_by(username=DEFAULT_ADMIN_USERNAME).first()
    if not existing:
        admin = AdminUser(
            username=DEFAULT_ADMIN_USERNAME,
            password_hash=hash_password(DEFAULT_ADMIN_PASSWORD),
            full_name="Administrator",
        )
        db.add(admin)
        db.commit()
        print(f"[SEED] Admin user '{DEFAULT_ADMIN_USERNAME}' created.")
    else:
        print(f"[SEED] Admin user '{DEFAULT_ADMIN_USERNAME}' already exists.")


def seed_fuel_types(db: Session):
    """Create default fuel types if not exists."""
    for fuel_name in FUEL_TYPES:
        existing = db.query(FuelType).filter_by(name=fuel_name).first()
        if not existing:
            fuel = FuelType(name=fuel_name, description=f"{fuel_name} fuel")
            db.add(fuel)
            print(f"[SEED] Fuel type '{fuel_name}' created.")
    db.commit()


def seed_nozzles(db: Session):
    """Create 8 nozzles if not exists."""
    for i in range(1, TOTAL_NOZZLES + 1):
        existing = db.query(Nozzle).filter_by(nozzle_number=i).first()
        if not existing:
            nozzle = Nozzle(
                nozzle_number=i,
                label=f"Nozzle {i}",
            )
            db.add(nozzle)
            print(f"[SEED] Nozzle {i} created.")
    db.commit()


def seed_tank_stock(db: Session):
    """Create tank stock entries (0 litres) for each fuel type."""
    fuel_types = db.query(FuelType).all()
    for fuel in fuel_types:
        existing = db.query(TankStock).filter_by(fuel_type_id=fuel.id).first()
        if not existing:
            stock = TankStock(
                fuel_type_id=fuel.id,
                current_stock_litres=0.0,
            )
            db.add(stock)
            print(f"[SEED] Tank stock for '{fuel.name}' initialized at 0 L.")
    db.commit()


def run_seed():
    """Execute all seed functions."""
    print("[SEED] Starting database seeding...")
    db = SessionLocal()
    try:
        seed_admin(db)
        seed_fuel_types(db)
        seed_nozzles(db)
        seed_tank_stock(db)
        print("[SEED] Database seeding complete.")
    except Exception as e:
        db.rollback()
        print(f"[SEED] Error during seeding: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    from database.engine import init_db
    init_db()
    run_seed()
