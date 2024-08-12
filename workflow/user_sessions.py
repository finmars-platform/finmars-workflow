import json
import logging
import sys
import threading
import traceback

_l = logging.getLogger('workflow')
import contextlib
import io

import sys
import matplotlib.pyplot as plt
import base64
import json

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
    # code_lines = code.split('\n')
    # if not '=' in code_lines[-1]:
    #     code_lines[-1] = f'print({code_lines[-1]})'
    # code = '\n'.join(code_lines)

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


def get_base_path():

    from workflow.models import Space
    space = Space.objects.all().first()

    return space.space_code


thread_local = threading.local()

# for execute_file method
def get_thread_local_buffers():
    # Initialize output and error buffers if they don't exist in the current thread
    if not hasattr(thread_local, 'output_buffer'):
        thread_local.output_buffer = io.StringIO()
    if not hasattr(thread_local, 'error_buffer'):
        thread_local.error_buffer = io.StringIO()
    return thread_local.output_buffer, thread_local.error_buffer

def _execute_code(code, context):
    # Get thread-local buffers
    output_buffer, error_buffer = get_thread_local_buffers()

    current_thread_id = threading.get_ident()
    _l.info(f"Executing code in thread ID: {current_thread_id}")

    with contextlib.redirect_stdout(output_buffer), contextlib.redirect_stderr(error_buffer):
        try:
            # Execute the code
            exec(code, context)
            error = error_buffer.getvalue()

            # Handle image output if matplotlib is used
            if plt.get_fignums():
                image_buffer = io.BytesIO()
                plt.savefig(image_buffer, format='png')
                plt.close()
                image_buffer.seek(0)
                image_data = base64.b64encode(image_buffer.read()).decode('utf-8')
                return {'type': 'image', 'data': image_data}

            # If no image, return text output
            output = output_buffer.getvalue()
            if output:
                try:
                    # Attempt to parse the output as JSON
                    json_output = json.loads(output)
                    return {'type': 'json', 'data': json_output}
                except json.JSONDecodeError:
                    # If not JSON, return as text
                    return {'type': 'text', 'data': output}
            elif error:
                return {'type': 'error', 'data': error}

        except Exception as e:
            # Handle any errors that occur during execution
            traceback_str = ''.join(traceback.format_exception(None, e, e.__traceback__))
            return {'type': 'error', 'data': traceback_str}

        finally:
            # Reset buffers for next use
            output_buffer.seek(0)
            output_buffer.truncate()
            error_buffer.seek(0)
            error_buffer.truncate()


def execute_file(user_id, file_path, data):
    session = sessions[user_id]
    context = {}

    _l.info('execute_file.context %s' % context)

    # Create a StringIO object to capture the standard output

    from workflow.storage import get_storage
    storage = get_storage()

    true_file_path = get_base_path() + '/' + file_path

    file = storage.open(true_file_path)

    content = file.read()

    context.update({'data': data})

    # _l.info('execute_file %s' % content)

    code = None

    if '.ipynb' in file_path:
        json_content = json.loads(content)
        code = json_content['cells'][0]['source']
    else:
        code = content

    return _execute_code(code, context)