import shutil
import os
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Copies CSS libraries from node_modules to static directory'

    def handle(self, *args, **options):
        css_libs = [
            'vuetify/dist/vuetify.css',
            'toastr/build/toastr.css',
        ]

        # Create the directory
        os.makedirs('workflow/static/css/', exist_ok=True)

        for lib in css_libs:
            src = f'node_modules/{lib}'
            dst = f'workflow/static/css/{lib.split("/")[-1]}'
            shutil.copy(src, dst)

        self.stdout.write(self.style.SUCCESS('Successfully copied CSS libraries to static directory'))
