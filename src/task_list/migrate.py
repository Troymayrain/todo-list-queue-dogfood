from task_list.database import database_path, migrate


def main() -> None:
    migrate()
    print(f"Database migrated: {database_path()}")


if __name__ == "__main__":
    main()
