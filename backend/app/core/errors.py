class ImaginaError(Exception):
    pass


class SessionNotFoundError(ImaginaError):
    def __init__(self, session_id: str):
        super().__init__(f"Session not found: {session_id}")
        self.session_id = session_id


class SessionStateError(ImaginaError):
    def __init__(self, msg: str):
        super().__init__(msg)


class TaskNotFoundError(ImaginaError):
    def __init__(self, task_id: str):
        super().__init__(f"Task not found: {task_id}")
        self.task_id = task_id
