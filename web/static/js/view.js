let configData = {};

$(window).on("load", function () {
    fetchSensorData();
    fetchConfigData();
    $('form').submit(updateConfigData);
    $('#wateringEnabled').change(function () {
        if (this.checked) {
            $('#minMoistureGroup').show();
        } else {
            $('#minMoistureGroup').hide();
        }
    });
});

function fetchSensorData() {
    $.getJSON("api/sensorData", onSensorDataReceived);
}

function fetchConfigData() {
    $.getJSON("api/configData", onConfigDataReceived);
}

function onSensorDataReceived(data) {
    $("#moistureVal").text(data["moisture"]);
    $("#temperatureVal").text(data["temperature"]);
    $("#lightVal").text(data["light"]);
}

function onConfigDataReceived(data) {
    configData = data;
    console.log(configData);
    $('#wateringEnabled').prop("checked", data["wateringEnabled"]);
    if (data["wateringEnabled"]) {
        $('#manualPumpButton').hide();
        $('#minMoistureGroup').show();
    } else {
        $('#manualPumpButton').show();
        $('#minMoistureGroup').hide();
    }
    $('#minMoisture').prop("value", data["wateringMinimumMoisture"]);
    $('#pumpingTime').prop("value", data["wateringPumpingTime"]);
    $('#healthMinTemp').prop("value", data["plantHealthMinimumTemperature"]);
    $('#healthMaxTemp').prop("value", data["plantHealthMaximumTemperature"]);
    $('#healthMinMoist').prop("value", data["plantHealthMinimumMoisture"]);
    $('#healthMaxMoist').prop("value", data["plantHealthMaximumMoisture"]);
}

function triggerShade() {
    $.post("api/shade", "", onShadeTriggered);
}

function onShadeTriggered(data) {
    let button = $("#shadeButton");
    if (data == 1) {
        button.text("Deactivate shade");
    } else if (data == 0) {
        button.text("Activate shade");
    } else {
        return;
    }

    button.prop("disabled", true);
    setTimeout(function () {
        button.prop("disabled", false)
    }, 3000);
}

function triggerPump() {
    $.post("api/manualPump", "", onPumpTriggered);
}

function onPumpTriggered() {
    let button = $("#manualPumpButton");
    button.prop("disabled", true);
    const timeout = configData["wateringPumpingTime"] ? (2.0 + configData["wateringPumpingTime"]) * 1000 : 20 * 1000;
    console.log(timeout);
    setTimeout(function () {
        button.prop("disabled", false)
    }, timeout);
}

function updateConfigData(event) {
    event.preventDefault();

    const changedValues = {};

    const isWateringEnabled = $('#wateringEnabled').is(':checked');
    if (isWateringEnabled !== configData.wateringEnabled) {
        changedValues.wateringEnabled = isWateringEnabled;
    }

    const wateringMinimumMoisture = parseFloat($('#minMoisture').val());
    if (wateringMinimumMoisture !== configData.wateringMinimumMoisture) {
        changedValues.wateringMinimumMoisture = wateringMinimumMoisture;
    }

    const wateringPumpingTime = parseFloat($('#pumpingTime').val());
    if (wateringPumpingTime !== configData.wateringPumpingTime) {
        changedValues.wateringPumpingTime = wateringPumpingTime;
    }

    const plantHealthMinimumTemperature = parseFloat($('#healthMinTemp').val());
    if (plantHealthMinimumTemperature !== configData.plantHealthMinimumTemperature) {
        changedValues.plantHealthMinimumTemperature = plantHealthMinimumTemperature;
    }

    const plantHealthMaximumTemperature = parseFloat($('#healthMaxTemp').val());
    if (plantHealthMaximumTemperature !== configData.plantHealthMaximumTemperature) {
        changedValues.plantHealthMaximumTemperature = plantHealthMaximumTemperature;
    }

    const plantHealthMinimumMoisture = parseFloat($('#healthMinMoist').val());
    if (plantHealthMinimumMoisture !== configData.plantHealthMinimumMoisture) {
        changedValues.plantHealthMinimumMoisture = plantHealthMinimumMoisture;
    }

    const plantHealthMaximumMoisture = parseFloat($('#healthMaxMoist').val());
    if (plantHealthMaximumMoisture !== configData.plantHealthMaximumMoisture) {
        changedValues.plantHealthMaximumMoisture = plantHealthMaximumMoisture;
    }

    console.log(JSON.stringify(changedValues, null, 2));

    $.ajax({
        url: '/api/configData',
        type: 'PATCH',
        contentType: 'application/json',
        data: JSON.stringify(changedValues),
        success: function (response) {
            console.log('Success:', response);
        },
        error: function (error) {
            console.log('Error:', error);
        }
    });
}