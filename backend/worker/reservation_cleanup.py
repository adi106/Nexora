import time

from sqlalchemy.orm import Session

from backend.app.db.session import SessionLocal
from backend.app.services.reservation_service import expire_pending_orders


CLEANUP_INTERVAL_SECONDS = 60


def run_cleanup_once(db: Session | None = None) -> int:
    """
    Run one reservation cleanup cycle.

    If a database session is supplied, it is used directly.
    Otherwise, a new application session is created.
    """

    owns_session = db is None

    if owns_session:
        db = SessionLocal()

    try:
        return expire_pending_orders(db)
    finally:
        if owns_session:
            db.close()


def run_worker() -> None:
    print("NEXORA reservation cleanup worker started.")

    while True:
        try:
            expired_count = run_cleanup_once()

            if expired_count:
                print(
                    f"Expired {expired_count} reservation(s)."
                )

        except Exception as exc:
            print(
                f"Reservation cleanup error: {exc}"
            )

        time.sleep(CLEANUP_INTERVAL_SECONDS)


if __name__ == "__main__":
    run_worker()