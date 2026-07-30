import os
from datetime import date, datetime, timedelta, timezone
from app.core.database import SessionLocal, engine, Base
from app.core.security import get_password_hash
from app.models.department import Department
from app.models.category import Category
from app.models.user import User, UserRole
from app.models.expense import Expense, ExpenseStatus
from app.models.reimbursement_request import ReimbursementRequest, RequestStatus
from app.models.audit_log import AuditLog


def seed():
    print("[*] Initializing Database Schema...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        print("[*] Seeding Departments...")
        eng_dept = Department(name="Engineering", code="ENG", budget=100000.0)
        sales_dept = Department(name="Sales", code="SALES", budget=75000.0)
        mktg_dept = Department(name="Marketing", code="MKTG", budget=50000.0)
        db.add_all([eng_dept, sales_dept, mktg_dept])
        db.commit()

        print("[*] Seeding Categories...")
        travel_cat = Category(name="Travel", description="Flight, train, hotel, or car rentals", max_limit_amount=2000.0)
        meals_cat = Category(name="Meals & Entertainment", description="Client dinners and team lunches", max_limit_amount=300.0)
        supplies_cat = Category(name="Office Supplies", description="Monitors, keyboards, desk accessories", max_limit_amount=500.0)
        software_cat = Category(name="Software & Cloud", description="Developer tools, SaaS subscriptions", max_limit_amount=1000.0)
        db.add_all([travel_cat, meals_cat, supplies_cat, software_cat])
        db.commit()

        print("[*] Seeding Demo Users...")
        admin_user = User(
            email="admin@company.com",
            full_name="System Administrator",
            hashed_password=get_password_hash("AdminPassword123!"),
            role=UserRole.ADMIN,
            department_id=eng_dept.id
        )

        eng_manager = User(
            email="manager.eng@company.com",
            full_name="Sarah Connor (Eng Manager)",
            hashed_password=get_password_hash("ManagerPassword123!"),
            role=UserRole.MANAGER,
            department_id=eng_dept.id
        )

        alice_employee = User(
            email="alice.eng@company.com",
            full_name="Alice Smith (Developer)",
            hashed_password=get_password_hash("EmployeePassword123!"),
            role=UserRole.EMPLOYEE,
            department_id=eng_dept.id
        )

        bob_employee = User(
            email="bob.sales@company.com",
            full_name="Bob Jones (Account Exec)",
            hashed_password=get_password_hash("EmployeePassword123!"),
            role=UserRole.EMPLOYEE,
            department_id=sales_dept.id
        )

        db.add_all([admin_user, eng_manager, alice_employee, bob_employee])
        db.commit()

        print("[*] Seeding Sample Expenses & Requests...")
        today = date.today()

        # Expense 1: Approved Flight
        exp1 = Expense(
            employee_id=alice_employee.id,
            category_id=travel_cat.id,
            amount=450.00,
            currency="USD",
            expense_date=today - timedelta(days=5),
            merchant="Delta Air Lines",
            description="Flight ticket to Tech Con 2026",
            status=ExpenseStatus.APPROVED
        )
        db.add(exp1)
        db.commit()

        req1 = ReimbursementRequest(
            expense_id=exp1.id,
            employee_id=alice_employee.id,
            status=RequestStatus.APPROVED,
            submission_date=datetime.now(timezone.utc) - timedelta(days=4),
            reviewer_id=eng_manager.id,
            decision_date=datetime.now(timezone.utc) - timedelta(days=3),
            manager_comment="Approved. Flight ticket within policy limit."
        )
        db.add(req1)

        # Expense 2: Pending Meal Expense
        exp2 = Expense(
            employee_id=alice_employee.id,
            category_id=meals_cat.id,
            amount=85.50,
            currency="USD",
            expense_date=today - timedelta(days=2),
            merchant="The Bistro Grill",
            description="Team lunch after sprint release",
            status=ExpenseStatus.SUBMITTED
        )
        db.add(exp2)
        db.commit()

        req2 = ReimbursementRequest(
            expense_id=exp2.id,
            employee_id=alice_employee.id,
            status=RequestStatus.PENDING,
            submission_date=datetime.now(timezone.utc) - timedelta(days=1),
            is_suspected_duplicate=False
        )
        db.add(req2)

        # Expense 3: Draft Keyboard Expense
        exp3 = Expense(
            employee_id=alice_employee.id,
            category_id=supplies_cat.id,
            amount=149.99,
            currency="USD",
            expense_date=today - timedelta(days=1),
            merchant="Keychron",
            description="Mechanical ergonomic keyboard",
            status=ExpenseStatus.DRAFT
        )
        db.add(exp3)

        # Expense 4: Rejected Sales Lunch
        exp4 = Expense(
            employee_id=bob_employee.id,
            category_id=meals_cat.id,
            amount=450.00,
            currency="USD",
            expense_date=today - timedelta(days=7),
            merchant="Luxury Steakhouse",
            description="Dinner with prospect",
            status=ExpenseStatus.REJECTED
        )
        db.add(exp4)
        db.commit()

        req4 = ReimbursementRequest(
            expense_id=exp4.id,
            employee_id=bob_employee.id,
            status=RequestStatus.REJECTED,
            submission_date=datetime.now(timezone.utc) - timedelta(days=6),
            reviewer_id=admin_user.id,
            decision_date=datetime.now(timezone.utc) - timedelta(days=5),
            manager_comment="Rejected. Amount exceeds $300 meal category limit."
        )
        db.add(req4)

        # Seed initial Audit Log entry
        audit = AuditLog(
            entity_type="SYSTEM",
            entity_id=1,
            action="SEED_DATABASE",
            actor_id=admin_user.id,
            actor_role="ADMIN",
            details={"message": "Initial database seed completed successfully."}
        )
        db.add(audit)
        db.commit()

        print("[+] Database seeding completed successfully!")
        print("\n[KEY] Demo Credentials:")
        print("--------------------------------------------------")
        print("ADMIN:       admin@company.com / AdminPassword123!")
        print("MANAGER:     manager.eng@company.com / ManagerPassword123!")
        print("EMPLOYEE 1:  alice.eng@company.com / EmployeePassword123!")
        print("EMPLOYEE 2:  bob.sales@company.com / EmployeePassword123!")
        print("--------------------------------------------------")

    except Exception as e:
        db.rollback()
        print(f"[-] Error seeding database: {e}")
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    seed()
