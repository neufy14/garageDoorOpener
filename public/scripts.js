//scripts.js

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
        })
        .catch(error => {
            console.error('Error fetching JSON:', error);
        });
}

// Function to display images and URLs
function displayImagesAndURLs(allURL) {
    // url = "/licensePlate/foundPlateImages/2024-01-13%2017%3A29%3A12.505965.jpg";
    // // Get the container element by its ID
    const imageContainer = document.getElementById('imageContainer2');

    // Loop through the array of image URLs
    allURL.forEach(url => {
        // Create an image element for each URL
        const imageElement = document.createElement('img');
        imageElement.src = url;
        imageElement.alt = 'Image';
        imageElement.style.maxWidth = '25%';
        imageElement.style.marginLeft = '4px';
        imageElement.style.marginRight = '4px';
        imageElement.style.marginTop = '10px';

        // Create a paragraph element for each URL
        const urlParagraph = document.createElement('p');
        urlParagraph.innerHTML = 'Image URL: ' + url;

        // Append the image and the paragraph to the container
        imageContainer.appendChild(imageElement);
        // imageContainer.appendChild(urlParagraph);
    });
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
    window.addEventListener('load', fetchImages);
}
function showCameraFeed(){
    camUrl = 'http://192.168.0.100/cgi-bin/snapshot.cgi?stream=0';
    const camImageContainer = document.getElementById('cameraFeed');
    const imageElement = document.createElement('img');
    imageElement.src = camUrl;
    camImageContainer.appendChild(imageElement)
}
function reloadLiveImage(){
    setInterval(() => {
        // Dynamically update the image source to fetch a new image
        document.getElementById('cameraFeed').src = 'http://192.168.0.100/cgi-bin/snapshot.cgi?stream=0' + new Date().getTime();
    }, 1000); // Refresh every 1 seconds
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
        const obj = await fetchLicensePlates();
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
function fetchLicensePlates() {
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
    fetchLicensePlates()
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
            return fetch('http://192.168.0.42:3000/save-to-file', {
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