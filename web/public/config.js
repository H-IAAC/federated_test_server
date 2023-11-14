function add (root, label, input) {
    var newLabelDiv = document.createElement('div');
    newLabelDiv.setAttribute('class','grid-child');

    var newLabel = document.createElement('label');
    newLabel.innerHTML = label + ':';

    var newInputDiv = document.createElement('div');
    newInputDiv.setAttribute('class','grid-child');

    var newInput = document.createElement('input');
    newInput.type = 'text';
    newInput.value = input;
    newInput.id = label;

    newLabelDiv.appendChild(newLabel);
    root.appendChild(newLabelDiv);

    newInputDiv.appendChild(newInput);
    root.appendChild(newInputDiv);
}
  
function remove (root) {
    while (root.firstChild) {
        root.removeChild(root.lastChild);
    }
}

function get (config_json) {

    let ret = {};
    jQuery.each(config_json, function(key, val) {      
        ret [key] = document.getElementById(key).value;
    });
    return ret;
}