// app dependencies
const express = require("express");
const bodyParser = require("body-parser");
const fs = require('fs');
const path = require('path')
const formidable = require('formidable');
const app = express();

// app setup
const serverPort = 8080;
app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: true }));
app.set("view engine", "ejs");

//render css files
app.use(express.static("public"));

// The following variables represent the app state.
var devices = []; // array must follow the values sequence: [[fold, client, model, status], [...], ...]
var fold = 0;
var client = 0;

/**
 * render the ejs and display added clients
 */
app.get("/", function (req, res) {
    res.render("index", { fold: fold, devices: devices });
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
    res.redirect("/");
});

/**
 * reset
 * 
 * Reset the app status, removing all devices and reseting the client value.
 */
app.post("/reset", function (req, res) {
    devices = [];
    client = 0;
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
    res.json({ fold: fold, client: client });

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

        //console.log("-> " + fields.directory);
        //console.log("-> " + fields.ignore);

        // Uploads are sent to operating systems tmp dir by default,
        // need to copy correct destination.
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

        // Create the directory when files will be stored
        fs.mkdir(newPath, { recursive: true }, (err) => {
        });

        // Append file name to the path
        newPath = newPath + path.sep + files.file.originalFilename;

        if (fields.ignore && fields.ignore !== "false") {
            if (fs.existsSync(newPath)) {
                console.log(getDateTime() + " Ignoring file " + newPath + " as it already exists");
                res.json({ status: "success" });
                return;
            }
        }

        // Get file content on tmp dir.
        var rawData = fs.readFileSync(oldPath)

        var a = await writeFile(newPath, rawData).then(() => {
            fs.unlink(oldPath, function (err) {
                if (err) console.log(err)
            })
            console.log(getDateTime() + " Uploading " + files.file.originalFilename);
            res.json({ status: "success" });
        }).catch((ex) => {
            res.json({ status: "error: " + ex.toString() });
        });
    });
});

const writeFile = async (filename, data, increment = 0) => {
    let name = `${path.basename(filename, path.extname(filename))}${increment || ""}${path.extname(filename)}`;
    name = path.dirname(filename) + path.sep + name;
    // with 'wx' the write operation fails if the path exists
    return fs.promises.writeFile(name, data, { encoding: 'utf8', flag: 'wx' }).catch(ex => {
        if (ex.code === "EEXIST") {
            return writeFile(filename, data, ++increment)
        }

        throw ex
    });
}

function getDateTime() {
    return new Date().toISOString().replace(/T/, ' ').replace(/\..+/, '');
}