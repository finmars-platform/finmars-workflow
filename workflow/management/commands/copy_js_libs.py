import shutil
import os
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Copies JavaScript libraries from node_modules to static directory"

    def handle(self, *args, **options):
        js_libs = [
            "vue/dist/vue.js",
            "vuex/dist/vuex.js",
            "vue-router/dist/vue-router.js",
            "vuetify/dist/vuetify.js",
            "moment/min/moment.min.js",
            "axios/dist/axios.min.js",
            "d3/dist/d3.min.js",
            "dagre-d3/dist/dagre-d3.min.js",
            "toastr/build/toastr.min.js",
            "jquery/dist/jquery.min.js",
        ]

        # Create the directory
        os.makedirs("workflow/static/scripts/", exist_ok=True)

        for lib in js_libs:
            src = f"node_modules/{lib}"
            dst = f"workflow/static/scripts/{lib.split('/')[-1]}"
            shutil.copy(src, dst)

        self.stdout.write(
            self.style.SUCCESS(
                "Successfully copied JavaScript libraries to static directory"
            )
        )
