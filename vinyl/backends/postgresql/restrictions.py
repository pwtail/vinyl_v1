from vinyl.restrict import Unused

class Restrictions:
    get_new_connection = Unused()
    ensure_timezone = Unused()  # TODO pool
    init_connection_state = Unused()
    create_cursor = Unused()
    check_constraints = Unused()
    is_usable = Unused()
    _nodb_cursor = Unused()
    pg_version = Unused()
