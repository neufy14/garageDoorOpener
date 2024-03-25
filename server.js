const express = require('express');
const bodyParser = require('body-parser');
const fs = require('fs/promises');
const path = require('path');
const { exec } = require('child_process');

const app = express();
const port = 3000;

app.use(bodyParser.urlencoded({ extended: true })); 

// Serve static files (including the HTML page)
app.use(express.static('public'));

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
    res.json({ message: 'Data received successfully' });
    // Find the user in the users array (you would typically query your database here)
    const user = users.find(u => u.username === username && u.password === password);
    console.log(user);
    if (user) {
        // Authentication successful
        console.log("successfully logged in")
        res.json({message: 'Login successful'});
    } else {
        // Authentication failed
        res.json({message: 'Login unsuccessful'});
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
