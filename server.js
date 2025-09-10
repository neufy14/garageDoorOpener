const express = require('express');
const bodyParser = require('body-parser');
const fsp = require('fs/promises');
const fs = require('fs');
const path = require('path');
const { exec, spawn } = require('child_process');
const AWS = require('aws-sdk');
const chokidar = require('chokidar');
let fetch;

const app = express();
const cors = require('cors');
const port = 3000;
const HLS_PORT = 8080;
const logFile = 'server.log';
const MAX_SIZE = 5 * 1024 * 1024; // 5MB
const NUM_SAVED_LOGS = 12;
var restartCounter = 0;
var numViewers = 0;
var doSendToS3 = false;

// Configure AWS
AWS.config.update({
    region: 'us-east-2',
});
const bucketName = 'garage-door-opener.s3.bucket';
const s3 = new AWS.S3();

app.use(bodyParser.urlencoded({ extended: true })); 

// setup stream paths
const HLS_DIR = path.join(__dirname, 'public/stream');
// const RTSP_URL = "//192.168.1.100:554/h264?username=admin&password=Steelers12"
const RTSP_URL = "rtsp://admin:Steelers12@192.168.1.100:554/h264cif";

// Start FFmpeg when the server starts
const ffmpegProcess = startFFmpeg();
const heartBeatCheck = checkHeartBeat();

// define allowed origins

const allowedOrigins = [
    'http://garage-door-opener.s3.bucket.s3-website.us-east-2.amazonaws.com',
    '192.168.1.42:3000',
    'https://edln4el6eah4qcrz7gxzad5jyy0gbvgi.lambda-url.us-east-2.on.aws/'
]

// Configure CORS to allow these origins
app.use(cors({
    origin: function (origin, callback) {
        if (!origin || allowedOrigins.includes(origin)) {
            callback(null, true); // Allow the request
        } else {
            callback(new Error('Not allowed by CORS')); // Block the request
        }
    },
}));

// Serve HLS files
app.use('/public/stream', express.static(HLS_DIR, {
    setHeaders: (res, path) => {
        if (path.endsWith('.ts')) {
            res.set('Content-Type', 'video/MP2T');
            res.set('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0');
        }
    }
}));


// Serve static files (including the HTML page)
app.use(express.static('public', {index: "login.html"}));

// Endpoint to fetch images
app.get('/images', async (req, res) => {
    console.log('start of something');
    try {
        // Replace 'path/to/your/image/folder' with the actual path to your image folder
        const folderPath = 'public/licensePlate/foundPlateImages';
        const files = await fsp.readdir(folderPath);
        const imageUrls = files.reverse().map(file => path.join('licensePlate/foundPlateImages', file));
	    console.log(files);
        res.json(imageUrls);
    } catch (error) {
        console.error(error);
        res.status(500).send('Internal Server Error');
    }
});

app.use(express.json());


// Sample users data (replace with your actual user database)
const users = [
    { username: 'alex', password: '71Upland71' },
    { username: 'lauren', password: '71Upland71' },
    { username: 'guest', password: '71Upland71' }
];
app.use(bodyParser.json());
// Login route handler
app.post('/login', (req, res) => {
    const username = req.body["username"];
    const password = req.body["password"];
    // const jsonData = req.body;
    // const jsonString = JSON.stringify(jsonData, null, 2);
    // console.log(jsonString["username"]);
    console.log('Usename from client:', req.body["username"]);
    // res.json({ message: 'Data received successfully' });
    // Find the user in the users array (you would typically query your database here)
    const user = users.find(u => u.username === username && u.password === password);
    console.log(user);
    if (user) {
        // Authentication successful
        console.log("successfully logged in")
        res.json({message: 'Login successful', loginStatus: true});
    } else {
        // Authentication failed
        res.json({message: 'Login unsuccessful', loginStatus: false});
    }
});

app.post('/save-to-file', (req, res) => {
    console.log("in post request")
    eval('var plateIdText = req.body.inputElements' + 0 + ";");
    var validPlates = {table: []}; 
    const jsonData = req.body;
    const jsonString = JSON.stringify(jsonData, null, 2);
    console.log(jsonString)

    // Write JSON data to a file
    console.log("about to write json")
    // fsp.writeFile('public/licensePlate/test.json', JSON.stringify(jsonData, null, 2), 'utf8', (err) => {
    fsp.writeFile('public/licensePlate/doorData.json', jsonString, (err) => {
        if (err) {
            console.error(err);
            res.status(500).send('Error writing to file');
        } else {
            res.send({'message': 'JSON file updated successfully.'});
        }
    });
    res.send({'message': 'JSON file updated successfully.'});
});
app.post('/runScript', (req, res) => {
    const pythonScript = 'public/licensePlate/doorOpener.py'; // Replace with your actual Python script
    console.log("running python script")
    exec(`python ${pythonScript}`, (error, stdout, stderr) => {
        if (error) {
            console.error(`Error executing Python script: ${error}`);
            res.status(500).send('Internal Server Error');
            return;
        }

        console.log('Python script output:', stdout);
        console.error('Python script errors:', stderr);
        res.send('Python script executed successfully!');
    });
});
app.post('/userLogOn', (req, res) => {
    logMessage("Someone logged in, starting stream");

    numViewers = numViewers + 1;
    // logMessage(jsonData[streamers])
    // ffmpegProcess = startFFmpeg();
    doSendToS3 = true
    res.send("Stream started");
})
app.post('/userLogOff', (req, res) => {
    logMessage("Someone logged off, checking if there are still active viewers");
    numViewers = numViewers - 1;
    if (numViewers < 1) {
        logMessage("No active viewers, stopping stream");
        doSendToS3 = false
        res.send("stopping stream")
    }
    else{
        res.send("Still active viewers, still streaming")
    }
})

app.listen(port, () => {
    console.log(`Server is running at http://localhost:${port}`);
});

// Middleware
app.use(bodyParser.urlencoded({ extended: true }));
app.use(express.static('public', { index: "login.html" }));
app.use(express.json());

// Start FFmpeg process to transcode RTSP to HLS
function startFFmpeg() {
    console.log('Starting FFmpeg to transcode RTSP to HLS...');
    logMessage("Starting FFmpeg to transcode RTSP to HLS...")
    // const ffmpeg = spawn('ffmpeg', [
    //     '-i', RTSP_URL, // Input RTSP stream
    //     '-c:v', 'libx264', // Video codec
    //     '-preset', 'veryfast', // Encoding preset
    //     '-crf', '28',
    //     '-b:v', '1M',
    //     '-g', '50', // GOP size
    //     '-hls_time', '2', // HLS segment length
    //     '-hls_list_size', '3', // Keep 3 segments in the playlist
    //     '-hls_flags', 'delete_segments', // Delete old segments
    //     '-f', 'hls', // Output format
    //     // '-stimeout', '5000000',
    //     '-r', '5',
    //     '-reconnect', '1',
    //     // '-reconnect_streamed', '0',
    //     // '-reconnect_delay_max', '2',
    //     // '-flags', 'low_delay',
    //     // '-fflags', 'nobuffer',
    //     '-force_key_frames', 'expr:gte(t,n_forced*2)',
    //     path.join(HLS_DIR, 'output.m3u8') // Output HLS playlist
    // ]);
    const ffmpeg = spawn('ffmpeg', [
        '-use_wallclock_as_timestamps', '1', // Use system clock for timestamps
        '-rtsp_transport', 'tcp', // More stable than UDP
        '-stimeout', '5000000', // Timeout in microseconds (5 seconds)
        '-reorder_queue_size', '0', // Helps reduce delay for broken GOPs
        '-fflags', '+nobuffer+discardcorrupt', // Reduce buffering delay
        '-i', RTSP_URL, // Input from IP camera
        '-threads', '1',
        '-c:v', 'libx264', // Encode with x264 for efficiency
        '-preset', 'ultrafast', // Reduce encoding delay
        '-tune', 'zerolatency', // Optimize for low latency
        '-crf', '28', // Control quality/bitrate tradeoff
        '-b:v', '1M', // Bitrate (adjust as needed)
        '-g', '25', // GOP size (match frame rate * keyframe interval)
        '-r', '5', // Frame rate (adjust based on bandwidth)
        '-flags', 'low_delay', // Optimize for low latency
        '-rtbufsize', '50M', // Buffer size to handle network fluctuations
        '-hls_time', '2', // Short segment duration for near real-time playback
        '-hls_list_size', '3', // Keep only 3 segments in the playlist
        '-hls_flags', 'delete_segments+append_list+program_date_time+discont_start+split_by_time', // Remove old segments
        '-hls_segment_type', 'mpegts', // Ensure compatibility
        '-force_key_frames', 'expr:gte(t,n_forced*1)', // Keyframe every 1 sec
        path.join(HLS_DIR, 'output.m3u8') // Output HLS stream
    ]);
    // ffmpeg.stdout.on('data', (data) => {
    //     logMessage(`FFmpeg stdout: ${data.toString()}`);
    //     // logMessage(`FFmpeg stdout: ${data.toString()}`);
    // });
    ffmpeg.stderr.on('data', (data) => {
        logMessage(`FFmpeg stderr: ${data.toString()}`);
        const keyPhrase = ["connection timed out", "network error", "broken pipe", "could not find stream", "could not find ref"];
        const found = keyPhrase.some(keyPhrase => data.includes(keyPhrase));
        // if (/connection timed out|network error|broken pipe|could not find stream|could not find ref/i.test(data)) {
        if (found) {
            logMessage('Detected connection error. Restarting FFmpeg...');
            restartFFmpeg();
        }
    });

    ffmpeg.on('close', (code, signal) => {
        logMessage(`FFmpeg process closed with code ${code} and signal ${signal}`);
        restartFFmpeg();
    });

    ffmpeg.on('error', (err) => {
        logMessage(`Failed to start FFmpeg: ${err}`);
        restartFFmpeg();
    });

    return ffmpeg;
}

function isMemorySufficient(minFreeMB = 300) {
    const freeMemMB = os.freemem() / (1024 * 1024); // Convert bytes to MB
    logMessage(`Available Memory: ${freeMemMB} MB`)
    return freeMemMB > minFreeMB;
}

async function waitForMemory(minMemoryMB, checkIntervalMS = 1000, maxChecks = 60) {
    let checks = 0;
    while (!isMemorySufficient) {
        await delay(checkIntervalMS);
        checks++
        if (checks > maxChecks) {
            logMessage("Waiting too long for memory drop, restarting FFmpeg anyways")
        }
    }
}

function restartFFmpeg() {
    logMessage("restarting...")
    restartCounter = restartCounter + 1;
    logMessage(`Number of restarts: ${restartCounter}`);
    stopFFmpeg();
    logMessage("startFFmpeg")
    setTimeout(startFFmpeg, 5000);
}

function stopFFmpeg(){
    if (ffmpegProcess) {
        logMessage("process exists, getting ready to kill")
        ffmpegProcess.kill();
        logMessage("killed process")
        // ffmpegProcess = null;
        // logMessage("end process")
    }
    ffmpeg = null
    waitForMemory(100)
}

function upload2S3(filepath, key) {
    if (doSendToS3) {
        console.log("uploading file: ", filepath);
        if (fs.existsSync(filepath)) {
            console.log("file exists")
            var cacheControlContent;
            const fileStream = fs.createReadStream(filepath);

            let contentType;
            if (filepath.endsWith('.m3u8')) {
                contentType = 'application/vnd.apple.mpegurl';
            } else if (filepath.endsWith('.ts')) {
                contentType = 'video/MP2T';
            } else {
                contentType = 'application/octet-stream';
            }

            if (key.endsWith('.ts')) {
                cacheControlContent = 'public, max-age=10';
            }
            else if (key.endsWith('.m3u8')) {
                cacheControlContent = 'public, max-age=3';
            }
            else {
                cacheControlContent = 'no-cache, no-store, must-revalidate';
            }
            

            const params = {
                Bucket: bucketName,
                Key: key,
                Body: fileStream,
                ContentType: contentType,
                CacheControl: cacheControlContent,
            };

            s3.upload(params, (err, data) => {
                if (err) {
                    console.error('Error uploading file: ', err);
                }
                else {
                    console.log('File uploaded successfully: ', data.Location);
                }
            });        
        }
        else {
            console.log("file did not exist");
        }        
    }
    else {
        console.log("No view, not sending to S3")
    }
}

function tsLog(message) {
    const timestamp = new Date().toLocaleString(); 
    console.log(`${timestamp} - ${message}`);
  }

const watcher = chokidar.watch(HLS_DIR, {
    persistent: true,
    ignoreInitial: true, // Ignore existing files when starting
});

watcher.on('add', (filepath) => {
    if (filepath.endsWith('.ts')) {
        const start = filepath.indexOf("output") + 6;
        const end = filepath.indexOf(".ts");
        const outputNum = Number(filepath.substring(start, end)) - 1;
        file2Upload = filepath.substring(0, start) + outputNum.toString() + ".ts";
        
        // console.log("Initial file = ", filepath);
        // console.log("start = ", start);
        // console.log("end = ", end);        
        // console.log("outputNum = ", outputNum);
        // console.log("file2Upload = ", file2Upload);
        // console.timeStamp(" - Adding .ts file")
        // console.log("Adding .ts file");
        const filename = path.basename(file2Upload);
        const s3Key = `public/streams/${filename}`;
        upload2S3(file2Upload, s3Key)
        // setTimeout(() => {
        //     upload2S3(filepath, s3Key)}, 600
        // );
    }
});

watcher.on('change', (filepath) => {
    if (filepath.endsWith('.m3u8')) {
        console.log("Adding .m3u8 file");
        logMessage("Adding .m3u8 file");
        const filename = path.basename(filepath);
        const s3Key = `public/streams/${filename}`;
        upload2S3(filepath, s3Key);
    }
    else if (filepath.endsWith('.ts')) {
        const start = filepath.indexOf("output") + 6;
        const end = filepath.indexOf(".ts");
        const outputNum = Number(filepath.substring(start, end)) - 1;
        file2Upload = filepath.substring(0, start) + outputNum.toString() + ".ts";
        // logMessage("Initial file = ", filepath);
        // logMessage("start = ", start);
        // logMessage("end = ", end);        
        // logMessage("outputNum = ", outputNum);
        // logMessage("file2Upload = ", file2Upload);
        // console.timeStamp(" - Adding .ts file")
        // console.log("Adding .ts file");
        const filename = path.basename(file2Upload);
        const s3Key = `public/streams/${filename}`;
        upload2S3(file2Upload, s3Key)
        // setTimeout(() => {
        //     upload2S3(filepath, s3Key)}, 600
        // );
    }
});
// Cleanup on exit
process.on('SIGINT', () => {
    console.log('Stopping FFmpeg...');
    logMessage('Stopping FFmpeg...');
    ffmpegProcess.kill('SIGINT');
    process.exit();
});

function deleteOldFiles() {
    fs.readdir(HLS_DIR, (err, files) => {
        if (err) {
            console.error('Error reading directory:', err);
            return;
        }

        const currentTime = Date.now();
        const expirationTime = 60 * 1000 * 5; // 5 minute in milliseconds

        files.forEach(file => {
            if (file.endsWith('.ts')) {
                const filePath = path.join(HLS_DIR, file);
                fs.stat(filePath, (err, stats) => {
                    if (err) {
                        console.error('Error getting file stats:', err);
                        return;
                    }

                    // If the file is older than 5 minute, delete it
                    if (currentTime - stats.mtimeMs > expirationTime) {
                        fs.unlink(filePath, (err) => {
                            if (err) {
                                console.error('Error deleting file:', err);
                            } else {
                                console.log(`Deleted old file: ${file}`);
                            }
                        });
                    }
                });
            }
        });
    });
}
function logMessage(message) {
    const timestamp = new Date().toISOString();
    if (fs.existsSync(logFile) && fs.statSync(logFile).size > MAX_SIZE) {
        rotateLogs();
    }
    fs.appendFileSync(logFile, `[${timestamp}] ${message}\n`, 'utf8');
}
function rotateLogs() {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-'); // Format timestamp
    const backupLog = `${logFile}.${timestamp}.bak`;

    fs.renameSync(logFile, backupLog); // Rename current log
    console.log(`Log rotated: ${backupLog}`);    
    const dir = path.dirname(logFile);
    const baseName = path.basename(logFile);

    const rotatedLogs = fs.readdirSync(dir)
        .filter(file => file.startsWith(baseName + '.') && file.endsWith('.bak'))
        .map(file => {
            const fullPath = path.join(dir, file);
            const stats = fs.statSync(fullPath);
            return {
                file: fullPath,
                mtime: stats.mtime
            };
        })
        .sort((a, b) => a.mtime - b.mtime);
    
        if (rotatedLogs.length > NUM_SAVED_LOGS) {
            const excess = rotatedLogs.length - NUM_SAVED_LOGS;
            for (let i = 0; i < excess; o=i++) {
                fs.unlinkSync(rotatedLogs[i].file);
                console.log(`Deleted old log: ${rotatedLogs[i].file}`)
            }
        }
}
async function checkHeartBeat() {
    if (!fetch) {
        fetch = (await import('node-fetch')).default;
    }
    setInterval(() => {
        console.log("checking heartbeat!")
        fetch("https://jv1idns9u3.execute-api.us-east-2.amazonaws.com/checkHeartbeat", {
            method: "POST",
            body: JSON.stringify({'hello': 'world'}),    
            headers: {
                "Content-Type": "application/json"
            }
        })
        .then(response => response.json())
        .then(data => {
            console.log(data)
            if (data == false) {
                doSendToS3 = false;
            }
            else if (data == true) {
                doSendToS3 = true;
            }
        })
        .catch(error => {
            console.error('Error fetching images:', error);
        });
    }, 60000); // ping every 60 seconds

}