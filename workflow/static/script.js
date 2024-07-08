function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
}

const notifyError = function (reason) {

    console.log('notifyError.reason', reason);

    let error_object = reason.response.data.error

    let message = ''

    message = message + '<span class="toast-error-field">Title</span>: ' + error_object.message + '<br/>'
    message = message + '<span class="toast-error-field">Code</span>: ' + error_object.status_code + '<br/>'
    message = message + '<span class="toast-error-field">URL</span>: ' + error_object.url + '<br/>'
    message = message + '<span class="toast-error-field">Username</span>: ' + error_object.username + '<br/>'
    message = message + '<span class="toast-error-field">Date & Time</span>: ' + error_object.datetime + '<br/>'
    message = message + '<span class="toast-error-field">Details</span>: <div><pre>' + JSON.stringify(error_object.details, null, 4) + '</pre></div>'

    let raw_title = 'Client Error'

    if (error_object.status_code === 500) {
        raw_title = 'Server Error'
    }

    let title = raw_title + '<span class="toast-click-to-copy">click to copy</span>'

    toastr.error(message, title, {
        progressBar: true,
        closeButton: true,
        tapToDismiss: false,
        onclick: function (event) {

            var listener = function (e) {

                e.clipboardData.setData('text/plain', JSON.stringify(error_object, null, 4));

                e.preventDefault();
            };

            document.addEventListener('copy', listener, false);

            document.execCommand("copy");

            document.removeEventListener('copy', listener, false);

        },
        timeOut: '10000',
        extendedTimeOut: '10000'
    });

    return Promise.reject(reason)

};

axios.interceptors.response.use(function (response) {
    // Any status code that lie within the range of 2xx cause this function to trigger
    // Do something with response data
    return response;
}, function (error) {
    // Any status codes that falls outside the range of 2xx cause this function to trigger
    // Do something with response error
    notifyError(error);
    return Promise.reject(error);
});


const router = new VueRouter({
    mode: "hash",
    routes: [
        {
            name: "home",
            path: "/",
        },
        {
            name: 'definitions',
            path: '/definitions'
        },
        {
            name: 'workers',
            path: '/workers'
        },
        {
            name: 'worfklow',
            path: '/item/:id'
        }
    ]
});

const store = new Vuex.Store({
    state: {
        definitions: [],
        workers: [],
        workflows: [],
        workflowsCount: 0,
        workflowNames: [],
        network: null,
        selectedWorkflow: null,
        selectedTask: null,
        taskIndex: null,
        loading: true,
        hideHooks: false,
        page_size: 40,
        query: null,
        page: 1,
    },
    actions: {
        listWorkflows({commit}) {

            const headers = {
                'Authorization': 'Token ' + getCookie('access_token'),
                'Accept': 'application/json',
                'Content-type': 'application/json'
            };

            let url = API_URL + "/workflow/light/?page_size=" + this.state.page_size + '&page=' + this.state.page

            if (this.state.query) {
                url = url + '&query=' + this.state.query
            }

            axios({
                method: 'get',
                url: url,
                headers: headers
            }).then((response) => {
                commit("updateWorkflows", response.data.results);
                commit("updateWorkflowsCount", response.data.count);
                commit("changeLoadingState", false);
            });
        },
        listDefinitions({
                            commit
                        }) {

            const headers = {
                'Authorization': 'Token ' + getCookie('access_token'),
                'Accept': 'application/json',
                'Content-type': 'application/json'
            };

            axios({method: 'get', url: API_URL + "/definition/", headers: headers}).then((response) => {
                commit('updateDefinitions', response.data)
                commit('changeLoadingState', false)
            })
        },
        listWorkers({
                            commit
                        }) {

            const headers = {
                'Authorization': 'Token ' + getCookie('access_token'),
                'Accept': 'application/json',
                'Content-type': 'application/json'
            };

            const url = `//${DOMAIN_NAME}/authorizer/api/v2/worker/?realm_code=${REALM_CODE}&app_code=workflow`;
            axios({method: 'get', url: url, headers: headers}).then((response) => {
                commit('updateWorkers', response.data.workers)
                commit('changeLoadingState', false)
            })
        },
        getWorkflow({commit}, workflow_id) {

            const headers = {
                'Authorization': 'Token ' + getCookie('access_token'),
                'Accept': 'application/json',
                'Content-type': 'application/json'
            };

            axios({
                method: 'get',
                url: API_URL + "/workflow/" + workflow_id + '/',
                headers: headers
            }).then((response) => {
                commit("updateSelectedWorkflow", response.data);
                commit("refreshNetwork", response.data.tasks);
                commit("changeLoadingState", false);
                if (response.data.tasks.length) {
                    commit("updateSelectedTask", response.data.tasks[0]);
                }
            });
        },
        selectTask({commit}, task) {
            commit("updateSelectedTask", task);
        },
        refreshStorage({commit, dispatch}) {

            const headers = {
                'Authorization': 'Token ' + getCookie('access_token'),
                'Accept': 'application/json',
                'Content-type': 'application/json'
            };

            axios({method: 'get', url: API_URL + "/refresh-storage/", headers: headers})
                .then((response) => {
                    dispatch("listWorkflows");
                    dispatch("listDefinitions");
                    dispatch("listWorkers");

                    toastr.success("Storage refreshed")

                });
        },
        relaunchWorkflow({commit, dispatch}, workflow_id) {

            const headers = {
                'Authorization': 'Token ' + getCookie('access_token'),
                'Accept': 'application/json',
                'Content-type': 'application/json'
            };

            axios
                .post(API_URL + "/workflow/" + workflow_id + "/relaunch/", headers)
                .then((response) => {
                    dispatch("listWorkflows");
                    dispatch("getWorkflow", response.data.id);
                });
        },
        cancelWorkflow({commit, dispatch}, workflow_id) {

            const headers = {
                'Authorization': 'Token ' + getCookie('access_token'),
                'Accept': 'application/json',
                'Content-type': 'application/json'
            };

            axios
                .post(API_URL + "/workflow/" + workflow_id + "/cancel/", headers)
                .then((response) => {
                    dispatch("listWorkflows");
                    dispatch("getWorkflow", response.data.id);
                });
        },
        updateQueryValue({commit}, value) {
            commit('updateQueryValue', value);
        },
        changePage({commit, dispatch}, page) {
            commit("setPage", page);
            dispatch("listWorkflows");
        },
    },
    mutations: {
        setPage(state, page) {
            state.page = page;
        },
        updateWorkflows(state, workflows) {
            state.workflows = workflows;
            console.log('workflows ', workflows)

            var filtered = workflows.filter(function (item) {
                return item.user_code
            })

            state.workflowNames = ["All"].concat([
                ...new Set(filtered.map((item) => item.user_code)),
            ]);
        },
        updateWorkflowsCount(state, count) {
            state.workflowsCount = count;
        },
        updateDefinitions(state, definitions) {
            state.definitions = definitions
        },
        updateWorkers(state, workers) {
            state.workers = workers
        },
        updateSelectedWorkflow(state, workflow) {
            state.taskIndex = null;
            state.selectedTask = null;
            state.selectedWorkflow = workflow;
        },
        updateSelectedTask(state, task) {
            state.selectedTask = task;
        },
        refreshNetwork(state, tasks) {
            var graphMain = new dagreD3.graphlib.Graph().setGraph({});
            var graphHook = new dagreD3.graphlib.Graph().setGraph({});

            var terminatedStatus = ["success", "cancel", "error"];

            var haveHook = false;

            for (let i = 0; i < tasks.length; i++) {
                if (tasks[i].is_hook && !terminatedStatus.includes(tasks[i].status)) {
                    continue;
                }

                var graph = graphMain;
                if (tasks[i].is_hook) {
                    graph = graphHook;
                    haveHook = true;
                }

                var className = tasks[i].status;
                var html = "<div class=pointer>";
                html += "<span class=status></span>";
                html += "<span class=name>" + tasks[i].name + "</span>";
                html += "<br>";
                html += "<span class=details>" + tasks[i].status + "</span>";
                html += "</div>";

                graph.setNode(tasks[i].celery_task_id, {
                    labelType: "html",
                    label: html,
                    rx: 3,
                    ry: 3,
                    padding: 0,
                    class: className,
                });

                if (tasks[i].previous) {
                    for (let j = 0; j < tasks[i].previous.length; j++) {
                        graph.setEdge(tasks[i].previous[j], tasks[i].celery_task_id, {});
                    }
                }
            }

            function initGraph(graph, svgClass) {
                // Set some general styles
                graph.nodes().forEach(function (v) {
                    var node = graph.node(v);
                    node.rx = node.ry = 5;
                });

                var svg = d3.select("svg." + svgClass),
                    inner = svg.select('g');

                // Set up zoom support
                var zoom = d3.zoom().on("zoom", function () {
                    inner.attr("transform", d3.event.transform);
                });
                inner.call(zoom.transform, d3.zoomIdentity);
                svg.call(zoom);

                // Create the renderer
                var render = new dagreD3.render();
                render(inner, graph);

                // Handle the click
                var nodes = inner.selectAll("g.node");
                nodes.on("click", function (task_id) {
                    graph.nodes().forEach(function (v) {
                        if (v == task_id) {
                            graph.node(v).style = "fill: #f0f0f0; stroke-width: 2px; stroke: #777;";
                        } else {
                            graph.node(v).style = "fill: white";
                        }
                    });

                    render(inner, graph);
                    state.selectedTask = tasks.find((c) => c.celery_task_id == task_id);
                });
            }

            state.hideHooks = !haveHook;

            Vue.nextTick(function () {
                initGraph(graphMain, "svg-main");
                initGraph(graphHook, "svg-hooks");
            });
        },
        changeLoadingState(state, loading) {
            state.loading = loading;
        },
        updateQueryValue(state, value) {
            state.page = 1;
            state.query = value;
        },
    },
    getters: {
        totalPages(state) {
            return Math.ceil(state.workflowsCount / state.page_size);
        },
        displayPages(state, getters) {
            let pages = [];
            let total_pages = getters.totalPages;
            for (let pageItem = 1; pageItem <= total_pages; pageItem++) {
                if (pageItem===1 || pageItem===state.page || pageItem===total_pages || Math.abs(pageItem-state.page)<=1){
                    pages.push(pageItem);
                }
                else{
                    pages.push('...');
                }
            }

            let result = [];
            for (let i = 0; i < pages.length; i++) {
                if (pages[i] !== pages[i + 1]) {
                    result.push(pages[i]);
                }
            }
            return result;
        },

    },
});

Vue.filter("formatDate", function (value) {
    if (value) {
        return moment.utc(value).local().format("YYYY-MM-DD HH:mm:ss Z");
    }
});

Vue.filter("statusColor", function (status) {
    if (status == "success") {
        return "#4caf50";
    } else if (status == "error") {
        return "#f44336";
    } else if (status == "init") {
        return "#f8f8f8";
    } else if (status == "canceled") {
        return "#b71c1c";
    } else if (status == "progress") {
        return "#2196f3";
    } else {
        return "#787777";
    }
});

Vue.filter("countTasksByStatus", function (workflows, status) {
    const tasks = workflows.filter((c) => c.status === status);
    return tasks.length;
});

new Vue({
    el: "#app",
    computed: {
        headers() {
            return [
                {
                    text: "Status",
                    align: "left",
                    value: "status",
                    width: "14%",
                    filter: (value) => {
                        if (this.selectedStatus.length == 0) return true;
                        return this.selectedStatus.includes(value);
                    },
                },
                {
                    text: "ID",
                    value: "id",
                    width: "16%",
                },
                {
                    text: "Name",
                    align: "left",
                    value: "fullname",
                    width: "40%",
                    filter: (value) => {
                        if (
                            !this.selectedWorkflowName ||
                            this.selectedWorkflowName == "All"
                        )
                            return true;
                        return value == this.selectedWorkflowName;
                    },
                },
                {
                    text: "Date",
                    align: "left",
                    value: "created",
                    width: "30%",
                },
            ];
        },
        ...Vuex.mapState([
            "definitions",
            "workers",
            "workflows",
            "workflowsCount",
            "workflowNames",
            "selectedWorkflow",
            "selectedTask",
            "taskIndex",
            "network",
            "loading",
            "hideHooks",
            "page"
        ]),
        ...Vuex.mapGetters(["totalPages", "displayPages"]),
        query: {
            get() {
                return this.$store.state.query;
            },
            set(value) {
                console.log('val', value)
                this.$store.dispatch('updateQueryValue', value);
            }
        }
    },
    store,
    router,
    vuetify: new Vuetify(),
    data: () => ({
                // navigation
        pageName: 'home',
        drawer: false,
        group: null,
        docLink: DOCUMENTATION_LINK,
        apiDocLink: API_DOCUMENTATION_LINK,
        logLink: LOG_LINK,
        // definitions
        multiLine: true,
        snackbar: false,
        dialog: false,
        postWorkflowResponse: "",
        dialogState: "",
        statusAlert: {success: "success", error: "error", pending: "pending", canceled: "canceled"},
        isWorkflowRun: false,
        payloadValue: "",
        selectedRunningWorkflow: null,
        postWorkflowErrorJSON: "",
        // workflow (home)
        autoRefresh: true,
        interval: null,
        tab: null,
        payloadDialog: false,
        relaunchDialog: false,
        cancelDialog: false,
        selectedStatus: [],
        status: ['init', "success", "error", "progress", "pending", "canceled"],
        selectedWorkflowName: "All",
    }),

    mounted() {
        this.$vuetify.theme.dark = true;
    },
    methods: {
        ...Vuex.mapActions(["changePage"]),
        moveUp: function () {
            window.scrollTo(0, 0);
        },
        getColor: function (status) {
            var color = {
                success: "green",
                error: "red",
                canceled: "red darken-4",
                warning: "orange",
                progress: "blue",
                init: "grey",
            }[status];
            return color;
        },
        selectRow: function (item) {
            // Catch to avoid redundant navigation to current location error
            this.$router
                .push({
                    name: "worfklow",
                    params: {
                        id: item.id,
                    },
                })
                .catch(() => {
                });

            window.location.reload() // TODO remove app reload on location change

            this.$store.dispatch("getWorkflow", item.id);


        },
        displayTask: function (task) {
            this.$store.dispatch("selectTask", task);
        },
        relaunchWorkflow: function () {
            this.$store.dispatch("relaunchWorkflow", this.selectedWorkflow.id);
            this.relaunchDialog = false;
        },
        refreshStorage: function () {
            this.$store.dispatch("refreshStorage");
        },
        refreshTask: function () {
            this.$store.dispatch("getWorkflow", this.selectedWorkflow.id);
        },
        goToHashUrl: function (hashUrl) {
            window.location.hash = hashUrl
            window.location.reload() // TODO Make location change without app reload
        },
        goToWorkerLogs: function() {
            const params = new URLSearchParams({
                realm_code: REALM_CODE,
                app_code: "workflow",
                worker_name: this.selectedWorkflow.tasks[0].worker_name,
                start_time: this.selectedWorkflow.tasks[0].created,
                end_time: this.selectedWorkflow.tasks[0].finished_at,
            })
            let url = `//${DOMAIN_NAME}/authorizer/api/v2/realm/0/log/?${params}`
            window.open(url, "_blank")
        },
        toggleAutoRefresh: function () {

            this.autoRefresh = !this.autoRefresh;

            if (this.autoRefresh) {
                this.interval = setInterval(() => {
                    this.$store.dispatch("listWorkflows");

                    let workflowID = this.$route.params.id;

                }, 5000);
            } else {
                clearInterval(this.interval);
            }
        },
        cancelWorkflow: function () {
            this.$store.dispatch("cancelWorkflow", this.selectedWorkflow.id);
            this.cancelDialog = false;
        },
        getFlowerTaskUrl: function () {
            if (this.selectedTask) {
                return FLOWER_URL + "/task/" + this.selectedTask.celery_task_id;
            }
            return "";
        },
        runButton: function (item) {
            (this.postWorkflowResponse = ""),
                (this.postWorkflowErrorJSON = ""),
                (this.payloadValue = ""),
                (this.dialog = true),
                (this.snackbar = false),
                (this.selectedRunningWorkflow = item);
        },

        runWorkflow: function () {
            this.snackbar = true;
            let payloadValueParsed;
            let payloadValueTrim = this.payloadValue.trim();
            this.dialogState = this.statusAlert.pending;
            this.isWorkflowRun = true;

            try {
                if (payloadValueTrim.length > 0) {
                    payloadValueParsed = JSON.parse(payloadValueTrim);
                } else {
                    payloadValueParsed = payloadValueTrim;
                }
            } catch (error) {
                this.postWorkflowErrorJSON = error;
            }

            let data = {
                user_code: this.selectedRunningWorkflow.user_code,
                payload: payloadValueTrim ? payloadValueParsed : {},
            };

            const headers = {
                'Authorization': 'Token ' + getCookie('access_token'),
                'Accept': 'application/json',
                'Content-type': 'application/json'
            };
            const urlWorkflow = API_URL + "/workflow/run-workflow/";
            axios
                .post(urlWorkflow, data, {headers: headers})
                .then((response) => {
                    this.postWorkflowResponse = response.data;
                    this.dialogState = this.statusAlert.success;
                })
                .catch((error) => {
                    this.postWorkflowResponse = error;
                    this.dialogState = this.statusAlert.error;
                })
                .finally(
                    () => (
                        (this.selectedRunningWorkflow = null), (this.isWorkflowRun = false)
                    )
                );
        },
        formattedTime(seconds) {
          if (!parseFloat(seconds)) {
              return 'N/A';
          }
          const days = Math.floor(seconds / 86400);
          const hours = Math.floor((seconds % 86400) / 3600);
          const minutes = Math.floor(((seconds % 86400) % 3600) / 60);
          const remainingSeconds = ((seconds % 86400) % 3600) % 60;

          return `${days}d ${hours}h ${minutes}m ${remainingSeconds}s`;
        },
    },
    created() {
        this.pageName = 'home';
        this.$store.dispatch('listWorkers');
        this.$store.dispatch('listDefinitions');
        this.$store.dispatch('listWorkflows');

        this.interval = setInterval(() => {

            this.$store.dispatch("listWorkflows");

            let workflowID = this.$route.params.id;

        }, 5000);

        let workflowID = this.$route.params.id;
        if (workflowID) {
            this.$store.dispatch("getWorkflow", workflowID);
        }


        if (this.$route.name === "definitions") {
            this.pageName = 'definitions';
        } else if (this.$route.name === "workers") {
            this.pageName = 'workers';
        }

    },
    beforeDestroy() {

    },
});
