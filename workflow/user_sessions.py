
import logging
_l = logging.getLogger('workflow')
import contextlib
import io

class UserSession:
    def __init__(self):
        self.files = {}

    def get_file_context(self, file_path):
        if file_path not in self.files:
            self.files[file_path] = {}
        return self.files[file_path]

sessions = {}

def create_session(user_id):
    sessions[user_id] = UserSession()

def execute_code(user_id, file_path, code):
    session = sessions[user_id]
    context = session.get_file_context(file_path)

    _l.info('execute_code.context %s' % context)

    # Create a StringIO object to capture the standard output
    stdout = io.StringIO()

    # Add print() to last line if it's not an assignment
    code_lines = code.split('\n')
    if not '=' in code_lines[-1]:
        code_lines[-1] = f'print({code_lines[-1]})'
    code = '\n'.join(code_lines)

    try:
        # Redirect the standard output to the StringIO object
        with contextlib.redirect_stdout(stdout):
            # Execute the code with the context as the local namespace
            exec(code, {}, context)
    except Exception as e:
        # Handle or raise the exception
        print(f"Error executing code: {str(e)}")
        raise e

    # Get the captured standard output
    output = stdout.getvalue()

    return output