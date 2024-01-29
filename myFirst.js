const express = require('express');
const request = require('request');

const app = express();
const port = 3000;

// Replace "http://your-ip-camera-url" with the actual URL of your IP camera
//const cameraUrl = "http://192.168.0.100/cgi-bin/snapshot.cgi";
const cameraUrl = "home/alex/licensePlate/foundPlateImages/2024-01-13 17:29:12.505965.jpg";
//const cameraUrl = "rtsp://admin:Steelers12@192.168.0.100/media/video1";



// Serve static files (HTML, CSS, etc.) from the 'public' directory
app.use(express.static('public'));


app.get('/', (req, res) => {
    // Fetch the image from the IP camera
    request.get(cameraUrl, { encoding: 'binary' }, (error, response, body) => {
        if (!error && response.statusCode === 200) {
            // Set the content type to image/jpeg
            res.writeHead(200, { 'Content-Type': 'image/png' });
            // Send the binary image data to the browser
            res.end(Buffer.from(body, 'binary'), 'binary');
        } else {
            // Handle errors (e.g., unable to fetch image)
            res.status(500).send('Error fetching image from the camera.');
        }
    });
});

app.listen(port, () => {
    console.log(`Server is running at http://localhost:${port}`);
});
