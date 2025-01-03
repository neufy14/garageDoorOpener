//scripts.js
var loggedIn = false;

function showDoorStatus() {
    var localstorage = "";
    const doorStatusText = document.getElementById('doorStatus');
    // Create a new paragraph element
    const paragraph = document.createElement('p');
    fetch("/licensePlate/doorData.json") 
        .then((res) => { 
            return res.json(); 
        })
        .then(data => {
            console.log(data);
            localstorage = JSON.stringify(data);
            const obj = JSON.parse(localstorage)
            console.log(localstorage);
            console.log(obj.doorStatus);
            console.log(obj.validLicensePlates)
            // Set the text content of the paragraph
            paragraph.innerHTML = 'The door is currently: ' + obj.doorStatus;
            // Append the paragraph to the body of the document
            doorStatusText.appendChild(paragraph);
            if (obj.doorStatus == "Closed"){
                document.getElementById('garageDoorButton').innerText = 'Open Door';
            }
            else {
                document.getElementById('garageDoorButton').innerText = 'Closed Door';
            }
        })
        .catch(error => {
            console.error('Error fetching JSON:', error);
        });
}
var lastImgNum = "";
// Function to display images and URLs
function displayImagesAndURLs(allURL) {
    // url = "/licensePlate/foundPlateImages/2024-01-13%2017%3A29%3A12.505965.jpg";
    // // Get the container element by its ID
    const imageContainer = document.getElementById('imageContainer2');
    const modal = document.getElementById('modal');
    const modalImg = document.getElementById('modal-img');
    imageContainer.style.display = 'grid';
    imageContainer.style.gridTemplateColumns = 'repeat(3, 1fr)';
    imageContainer.style.gap = '20px';
    var numImages = 0;
    modal.addEventListener('keydown', function(event) {
        console.log(event.key);
        if (event.key == "ArrowLeft") {
            console.log("Arrow pressed");
        }
    });    
    // Loop through the array of image URLs
    allURL.forEach(url => {
        var imageId = "img" + numImages;
        console.log(imageId);
        const galleryItem = document.createElement("div");
        galleryItem.className = "gallery-item";
        galleryItem.style.width = '100%';

        const galleryBorder = document.createElement("fieldset");

        // Create an image element for each URL
        const imageElement = document.createElement('img');
        imageElement.src = url;
        imageElement.alt = 'Image';
        // galleryItem.style.flex = '0 0 calc(33.33% - 20px)';
        // galleryItem.style.position = 'relative';
        imageElement.style.maxWidth = '100%';
        imageElement.style.marginLeft = '4px';
        imageElement.style.marginRight = '4px';
        imageElement.style.marginTop = '10px';
        imageElement.id = imageId;
        imageElement.addEventListener('mouseenter', function() {
            this.style.transform = 'scale(1.1)';
        });
        imageElement.addEventListener('mouseleave', function() {
            this.style.transform = 'scale(1)';
        });
        imageElement.addEventListener('click', function(event) {
            if (event.target.tagName == "IMG") {
                console.log(event.target);
                console.log(event.target.src);
                console.log(event.target.id);
                lastImgNum = event.target.id;
                // Open modal and display clicked image
                modalImg.src = event.target.src;
                // modal.id = event.target.id;
                document.getElementById(modal.id).setAttribute(modal.id, event.target.id);
                modalImg.style.maxWidth = '75%';
                modal.style.display = 'block';
            }
        });

        // Create a paragraph element for each URL
        const urlParagraph = document.createElement('p');
        const lastSlash = url.lastIndexOf("/") + 1;
        const lastdot = url.lastIndexOf(".");
        urlParagraph.innerHTML = url.substring(lastSlash, lastdot);
        urlParagraph.style.maxWidth = '100%';

        // Append the image and the paragraph to the container
        
        galleryItem.appendChild(urlParagraph);
        galleryItem.appendChild(imageElement);
        galleryBorder.appendChild(galleryItem);
        imageContainer.appendChild(galleryBorder);
        numImages += 1;
    });
    scrollModal();
}
function fetchImages(){
    // displayImagesAndURLs();
    fetch("/images") // Fetch data from the server endpoint
        .then(response => response.json())
        .then(images => {
            displayImagesAndURLs(images);
        })
        .catch(error => {
            console.error('Error fetching images:', error);
        });
}
function loadScript() {
    // Add an event listener to the body, triggering the display function on load
    console.log("loading index page")
    window.addEventListener('load', fetchImages);
    // window.addEventListener('load', scrollModal);
}
function scrollModal() {
    // Close the modal when the close button or overlay is clicked
    const modalImg = document.getElementById('modal-img');
    modal.addEventListener('click', function(event) {
        console.log(lastImgNum)
        if (event.target.classList.contains('modal') || event.target.classList.contains('close')) {
            modal.style.display = 'none';
        }
        else if (event.target.classList.value == "arrow right") {
            console.log("right arrow pressed")
            var newImgNum = (parseInt(lastImgNum.substring(3)) + 1);
            console.log("img" + newImgNum.toString());
        }
        else if (event.target.classList.value == "arrow left") {
            console.log("left arrow pressed")
            var newImgNum = (parseInt(lastImgNum.substring(3)) - 1);
            console.log("img" + newImgNum.toString());
        }
        var newImageSrc = document.getElementById("img" + newImgNum.toString()).src;
        modalImg.src = newImageSrc;
        // modal.id = event.target.id;
        document.getElementById(modal.id).setAttribute(modal.id, event.target.id);
        modalImg.style.maxWidth = '75%';
        modal.style.display = 'block';
        lastImgNum = "img" + newImgNum.toString();
    });

}
function showCameraFeed(){
    camUrl = 'http://192.168.1.100/cgi-bin/snapshot.cgi?stream=0';
    const camImageContainer = document.getElementById('cameraFeed');
    const imageElement = document.createElement('img');
    imageElement.src = camUrl;
    imageElement.id = 'liveViewImg';
    imageElement.width = 1500;
    imageElement.height = imageElement.width / 1.8;
    camImageContainer.appendChild(imageElement)
}
function reloadLiveImage(){
    // setInterval(() => {
    //     // Dynamically update the image source to fetch a new image
    //     document.getElementById('cameraFeed').src = 'http://192.168.1.100/cgi-bin/snapshot.cgi?stream=0';
    // }, 100); // Refresh every 1 seconds
    setInterval(imageReload, 66)
    function imageReload() {
        document.getElementById('liveViewImg').src = 'http://192.168.1.100/cgi-bin/snapshot.cgi?stream=0';
        // console.log("current time = ");
        // console.log(Date.now());
    }
}
function openNav() {
    document.getElementById("mySidebar").style.width = "250px";
    document.getElementById("main").style.marginLeft = "250px";
}

function closeNav() {
    document.getElementById("mySidebar").style.width = "0";
    document.getElementById("main").style.marginLeft= "0";
}
var _counter = 0;
function addPlates(action) {
    console.log("Clicked!")
    if (action == "add") {
        _counter++;
        var originalElement = null;
        var originalElement = document.getElementById("template");
        var oClone = originalElement.cloneNode(true);
        
        oClone.id += (_counter + "");
        oClone.className = 'added';
        console.log(oClone.id);
        document.getElementById("newItem").appendChild(oClone);
        var clonedInput = oClone.querySelectorAll('input');
        var deleteButtonElement = document.querySelectorAll('.deleteButton');
        var inputElements = document.querySelectorAll('div.columnInput input');
        clonedInput.forEach(function (input) {
            input.value = '';
        });
        for (var i = 0; i < deleteButtonElement.length; i++) {
            deleteButtonElement[i].id = 'deleteButtonId-' + i;
            deleteButtonElement[i].name = 'deleteButtonElement' + i;
        }
        for (var i = 0; i < inputElements.length; i++) {
            inputElements[i].id = 'inputElementsId-' + i;
            inputElements[i].name = 'inputElements' + i;
        }
        var originalStyles = window.getComputedStyle(document.getElementById("template"));
        var clonedStyles = oClone.style;
        var clonedValues = oClone.value;
        for (var i = 0; i < originalStyles.length; i++) {
            var styleName = originalStyles[i];
            clonedStyles[styleName] = originalStyles[styleName];

        } 
    }
}
function removePlate(obj) {
    console.log("Delete Clicked!")
    console.log(obj.parentNode.className)
    console.log(obj.parentNode.id)
    if (obj.parentNode.className == 'added') {
        obj.parentNode.parentNode.removeChild(obj.parentNode);
        _counter--;
    }
}
function loadPlateScript() {
    // Add an event listener to the body, triggering the display function on load
    window.addEventListener('load', async function() {
        const obj = await fetchJson();
        console.log(obj.doorStatus);
        console.log(obj.validLicensePlates);
        for (var i = 0; i < Object.keys(obj.validLicensePlates).length; i++) {
            console.log(Object.keys(obj.validLicensePlates)[i]);
            var name = Object.keys(obj.validLicensePlates)[i];
            var plate = obj.validLicensePlates[name];
            console.log(plate)
            if (i > 0) {
                addPlates("add")
            }
            var plateIdText = "inputElementsId-" + (i*2);
            var nameIdText = "inputElementsId-" + ((i*2)+1);
            console.log(nameIdText);
            document.getElementById(plateIdText).value = plate;
            document.getElementById(nameIdText).value = name;
        }
    });
    
}
function fetchJson() {
    return fetch("/licensePlate/doorData.json") 
    .then((res) => { 
        return res.json(); 
    })
    .then(data => {
        localstorage = JSON.stringify(data);
        const obj = JSON.parse(localstorage);
        return new Promise(resolve => {
            console.log(obj);
            resolve(obj);
        });
        
    })
    .catch(error => {
        console.error('Error fetching JSON:', error);
    });
}
function saveLicensePlates() {
    fetchJson()
        .then(result => {
            const existingPlates = result;
            console.log("Save button pressed!")
            console.log(existingPlates)
            var validPlates = {validLicensePlates: []};
            console.log("existing plate log")
            console.log(existingPlates.validLicensePlates);
            existingPlates.validLicensePlates = {};
            console.log(existingPlates);
            var newJsonData = {};
            for (var i = 0; i <= _counter; i++) {
                var plateIdText = "inputElementsId-" + (i*2);
                var nameIdText = "inputElementsId-" + ((i*2)+1);
                var plate = document.getElementById(plateIdText).value;
                var name = document.getElementById(nameIdText).value;
                existingPlates.validLicensePlates[name] = plate
            }
            console.log(existingPlates)
            // existingPlates.validLicensePlates.push(newJsonData);
            // Send a POST request to the server
            return fetch('http://192.168.1.42:3000/save-to-file', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(existingPlates),
            })
            .then(response => response.text())
            .then(data => {
                console.log(data);
            })
            .catch(error => {
                console.error('Error:', error);
            });
        })
        .catch(error => {
            console.error('Error:', error);
        });

}
function runScript() {
    fetch("/licensePlate/doorData.json") 
    .then((res) => { 
        return res.json(); 
    })
    .then(data => {
        localstorage = JSON.stringify(data);
        const obj = JSON.parse(localstorage)
        if (obj.doorStatus == "Closed"){
            document.querySelector('garageDoorButton').value = 'Closed';
        }
        else if (obj.doorStatus == "Open"){
            document.querySelector('garageDoorButton').value = 'Open';
        }

    })
    .catch(error => {
        console.error('Error fetching JSON:', error);
    });    
    fetch('/runScript')
        .then(response => response.text())
        .then(data => console.log(data))
        .catch(error => console.error('Fetch error:', error));

}
function submitLogin() {
    console.log("submit button pressed");
    const userData = {username: document.getElementById("first").value, password: document.getElementById("password").value};
    console.log(userData);
    // Send a POST request to the server
    fetch("/login", {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(userData),
    })
    .then(response => {
        if (response.ok) {
            console.log("Network response was OK")
            return response.json(); // If the response is OK, parse it as JSON
        } else {
            console.log(responses)
            throw new Error("Network response was not ok.");
        }
    })
    .then(data => {
        console.log(data["loginStatus"]); // Handle the response data
        if (data["loginStatus"] == true) {
            console.log("logging in")
            loggedIn = true;
            console.log(loggedIn)
            window.location.href = 'index.html';
        }
        // Redirect or perform other actions based on the response
    })
    .catch(error => {
        console.error("There was a problem with the fetch operation:", error);
    });   
}
function runCheckPlateProgram() {
    console.log("runCheckProgram")
    const runLicenseProgram = document.getElementById("runProgramToggle").checked;
    console.log("program status = ", runLicenseProgram);
    fetch("/licensePlate/doorData.json") 
    .then((res) => { 
        return res.json(); 
    })
    .then(data => {
        localstorage = JSON.stringify(data);
        const obj = JSON.parse(localstorage)
        console.log(obj)
        if (runLicenseProgram == true){
            obj["runProgram"] = true;
        }
        else if (runLicenseProgram == false){
            obj["runProgram"] = false;
        }
        return fetch('http://192.168.1.42:3000/save-to-file', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(obj),
        })
        .then(response => response.text())
        .then(data => {
            console.log(data);
        })
        .catch(error => {
            console.error('Error:', error);
        });
    })
    .catch(error => {
        console.error('Error fetching JSON:', error);
    });    
}
function getSettings() {
    console.log("on load get settings")
    window.addEventListener('load', async function() {
        const obj = await fetchJson();
        console.log("program status at load = ", obj.runProgram);
        document.getElementById("runProgramToggle").checked = obj.runProgram;
    });
}
function checkLogin() {
    console.log("checking login")
    console.log(loggedIn)
    if(loggedIn == false) {
        // window.location.href = 'login.html';
        console.log("redirected because not logged in")
    }
}
function hlsStream() {
    const video = document.getElementById('video');
    const streamUrl = '/stream/output.m3u8';
    var player = videojs(vid1);
    // player.play();

    // if (Hls.isSupported()) {
    //     console.log("hls is supported");
    //     const hls = new Hls();
    //     hls.loadSource(streamUrl);
    //     hls.attachMedia(video);
    //     hls.on(Hls.Events.MANIFEST_PARSED, () => {
    //         video.play();
    //     });
    // } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
    //     console.log("hls is not supported");
    //     video.src = streamUrl;
    // } else {
    //     console.error('HLS is not supported in this browser.');
    // }
}