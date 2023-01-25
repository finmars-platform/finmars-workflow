# initialize a working context

from director import create_app
from director.extensions import cel

app = create_app()
app.app_context().push()