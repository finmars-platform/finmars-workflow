
import logging
import sys
import traceback

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

    # Capture stdout
    old_stdout = sys.stdout
    redirected_output = sys.stdout = io.StringIO()

    # Execute the code
    try:
        exec(code, context)
    except Exception as e:
        # Print the traceback of the error
        traceback.print_exc(file=redirected_output)

    # Reset stdout
    sys.stdout = old_stdout

    return redirected_output.getvalue()