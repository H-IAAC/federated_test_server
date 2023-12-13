// app dependencies
const express = require("express");
const bodyParser = require("body-parser");
const fs = require('fs');
const path = require('path')
const utils = require('./utils/utils');
const formidable = require('formidable');
const app = express();

// app setup
var serverPort = 8080;
app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: true }));
app.set("view engine", "ejs");

//render css files
app.use(express.static("public"));

// The following variables represent the app state.
var devices = []; // array must follow the values sequence: [[fold, client, model, status], [...], ...]
var fold = 0;
var client = -1;
var flower_server = 'vm.hiaac.ic.unicamp.br';
var flower_port = '8083';
var flower_api_port = '8082';
var algorithm_name = 'FedAvg';
var algorithm_params = '{}';

// parse command line args
const args = process.argv.slice(2);
switch (args[0]) {
    case '-h':
        console.log('Usage:');
        console.log('  -p <port_number>');
        console.log('');
        return;

    case '-p':
        if (args[1] === undefined) {
            console.log('Missing the port value.');
            return;
        }
        serverPort = args[1];
        break;

    default:
        console.log('Invalid argument: ' + args[2]);
}


/**
 * render the ejs and display added clients
 */
app.get("/", function (req, res) {
    res.render("index", { fold: fold,
                          devices: devices,
                          flower_server: flower_server,
                          flower_port: flower_port,
                          flower_api_port:flower_api_port,
                          algorithm_name: algorithm_name,       // name of the latest selected algorithm
                          algorithm_params: algorithm_params,   // params of the latest selected algorithm
                          algorithms_options: JSON.stringify(utils.get_config()) }); // always return the config file content
});

/**
 * set app to listen on port 'serverPort'
 */
app.listen(serverPort, function () {
    console.log("--- H-IAAC - Federated Test ---");
    console.log("server is running on port " + serverPort);
});

/**************************************************/
/** Bellow APIs are related to the web frontend. **/
/**************************************************/
/**
 * setConfig
 * 
 * Change the 'fold' value returned on 'getConfig'
 */
app.post("/setConfig", function (req, res) {
    fold = req.body.fold;
    flower_server = req.body.flower_url;
    flower_port = req.body.flower_port;
    flower_api_port = req.body.flower_api_port;
    algorithm_name = req.body.algorithm_name;       // receive the selected algorithm
    algorithm_params = req.body.algorithm_params;   // receive the entered algorithm params
    res.redirect("/");
});

/**
 * reset
 * 
 * Reset the app status, removing all devices and reseting the client value.
 */
app.post("/reset", function (req, res) {
    devices = [];
    client = -1;
    res.redirect("/");
});

/**
 * getDevices
 * 
 * Return a list of devices/clients attached to this server.
 */
app.get("/getDevices", function (req, res) {
    res.json({ devices: devices });
});

/**************************************************/
/** Bellow APIs are related to the Android app. ***/
/**************************************************/
/**
 * getConfig
 * 
 * Returns the configuration to be used by the app, eg.:
 *   {
 *     "fold": "2",
 *     "client": 4
 *   }
 */
app.get("/getConfig", function (req, res) {
    client++;
    res.json({ fold: fold, client: client,
               flower_server: flower_server,
               flower_port: flower_port,
               flower_api_port: flower_api_port,
               algorithm_name: algorithm_name,          // algorithm name, selected by the user
               algorithm_params: algorithm_params});    // the algorithm entered by the user
});

/**
 * addDevice
 * 
 * Used to inform the server that a device/client is running.
 */
app.post("/addDevice", function (req, res) {
    var device = [req.body.fold, req.body.client, req.body.model, req.body.status];

    if (req.body.fold != fold)
        device[3] = "Invalid Fold, using [" + req.body.fold + "] instead of [" + fold + "]";

    //add the new device from the post route
    devices.push(device);
    res.json({ status: "success" });
});

/**
 * setDeviceStatus
 * 
 * Change the status from a device.
 */
app.post("/setDeviceStatus", function (req, res) {
    var device = [req.body.client, req.body.status];

    var deviceClientId = req.body.client;

    for (var i = 0; i < devices.length; i++) {
        if (devices[i][1] == deviceClientId) {
            devices[i][3] = devices[i][3] + "<br/> -" + req.body.status;
            res.json({ status: "success" });
            return;
        }
    }

    res.json({ status: "id not found" });
});

app.post("/upload", function (req, res) {

    var ret = { status: "" };
    const form = new formidable.IncomingForm();

    // Parse form content
    form.parse(req, async function (err, fields, files) {
        if (!files.file || !files.file.filepath) {
            console.log(getDateTime() + " Missing files parameters, not file received.");
            return;
        }
            
        var oldPath = files.file.filepath;

        // Checks if need to create a new directory
        var newPath;
        if (fields.directory) {
            // Files must be stored on directory inside 'uploads' directory
            newPath = path.join(__dirname, 'uploads') + path.sep + fields.directory;
        } else {
            // Files must be stored on 'uploads' directory
            newPath = path.join(__dirname, 'uploads');
        }

        console.log(getDateTime() + " New upload request to [" + fields.directory + "] [" + files.file.originalFilename + "] success.");

        // Create the directory when files will be stored
        if (!fs.existsSync(newPath)) {
            fs.mkdirSync(newPath, { recursive: true }   );
        }

        // Append file name to the path
        newPath = newPath + path.sep + files.file.originalFilename;

        if (fields.ignore && fields.ignore !== "false") {
            if (fs.existsSync(newPath)) {
                console.log(getDateTime() + " Ignoring file [" + newPath + "] as it already exists");
                res.json({ status: "success" });
                return;
            }
        }

        // Get file content on tmp dir.
        try {
            fs.renameSync(oldPath, newPath);
            res.json({ status: "success" });
            console.log(getDateTime() + " Uploading to [" + newPath + "] success.");
        } catch (ex) {
            console.log(getDateTime() + " Uploading to [" + newPath + "] failed. " + ex.toString());
            res.json({ status: "error: " + ex.toString() });
        }
    });
});

function getDateTime() {
    return new Date().toISOString().replace(/T/, ' ').replace(/\..+/, '');
}
