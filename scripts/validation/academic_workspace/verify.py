"""Replay migrations, insert fictional college data and test actual PostgreSQL."""

from runtime import database, replay, run_file
from concurrency import verify_concurrent_duplicate


def main():
    with database() as container:
        replay(container)
        for name in ("seed.sql", "integrity.sql", "rejections.sql", "lifecycle.sql"):
            print(f"CHECK {name}", flush=True)
            run_file(container, name)
        verify_concurrent_duplicate(container)
        run_file(container, "summary.sql")
    print("PASS: fictional database validated and run-owned container removed", flush=True)


if __name__ == "__main__":
    main()
