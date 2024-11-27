const express = require('express');
const bodyParser = require('body-parser');
const fs = require('fs/promises');
const path = require('path');
const { exec, spawn } = require('child_process');

const app = express();
const port = 3000;
const HLS_PORT = 8080;

app.use(bodyParser.urlencoded({ extended: true })); 

// setup stream paths
const HLS_DIR = path.join(__dirname, 'public/stream');
// const RTSP_URL = "//192.168.1.100:554/h264?username=admin&password=Steelers12"
const RTSP_URL = "rtsp://admin:Steelers12@192.168.1.100:554/h264cif";

// stream to s3 variables
const program2check = "stream2S3.js";
const streaming2S3 = False;

// Start FFmpeg when the server starts
const ffmpegProcess = startFFmpeg();

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
        const files = await fs.readdir(folderPath);
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
    { username: 'user1', password: 'password1' },
    { username: 'user2', password: 'password2' }
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
    // fs.writeFile('public/licensePlate/test.json', JSON.stringify(jsonData, null, 2), 'utf8', (err) => {
    fs.writeFile('public/licensePlate/doorData.json', jsonString, (err) => {
        if (err) {
            console.error(err);
            res.status(500).send('Error writing to file');
        } else {
            res.send('Data saved to file successfully');
        }
    });
});
app.get('/runScript', (req, res) => {
    const pythonScript = 'public/licensePlate/doorOpener.py'; // Replace with your actual Python script

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

app.listen(port, () => {
    console.log(`Server is running at http://localhost:${port}`);
});

// Middleware
app.use(bodyParser.urlencoded({ extended: true }));
app.use(express.static('public', { index: "login.html" }));
app.use(express.json());

// Start FFmpeg process to transcode RTSP to HLS
function startFFmpeg() {
    exec(`pgrep -x ${targetProgram}`, (err, stdout, stderr) => {
        if (err || stderr) {
            console.log(`${targetProgram} is not running.`);
            streaming2S3 = False;
        } else if (stdout) {
            console.log(`${targetProgram} is running with PID(s):`, stdout.trim());
            streaming2S3 = True;
        }
    });
    console.log('Starting FFmpeg to transcode RTSP to HLS...');
    const ffmpeg = spawn('ffmpeg', [
        '-i', RTSP_URL, // Input RTSP stream
        '-c:v', 'libx264', // Video codec
        '-preset', 'veryfast', // Encoding preset
        '-crf', '28',
        '-b:v', '1M',
        '-g', '50', // GOP size
        '-hls_time', '2', // HLS segment length
        '-hls_list_size', '3', // Keep 3 segments in the playlist
        '-hls_flags', 'delete_segments', // Delete old segments
        '-f', 'hls', // Output format
        // '-stimeout', '5000000',
        '-r', '5',
        // '-flags', 'low_delay',
        // '-fflags', 'nobuffer',
        '-force_key_frames', 'expr:gte(t,n_forced*2)',
        path.join(HLS_DIR, 'output.m3u8') // Output HLS playlist
    ]);

    ffmpeg.stderr.on('data', (data) => {
        console.error(`FFmpeg stderr: ${data.toString()}`);
    });

    ffmpeg.on('close', (code) => {
        console.log(`FFmpeg exited with code ${code}`);
    });

    return ffmpeg;
}

// Cleanup on exit
process.on('SIGINT', () => {
    console.log('Stopping FFmpeg...');
    ffmpegProcess.kill('SIGINT');
    process.exit();
});