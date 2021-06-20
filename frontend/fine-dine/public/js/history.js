// Global variables
BASE_URL = "https://admin-fine-dine.herokuapp.com/api/v1/admin"


function getCookie(name) {
    var nameEQ = name + "=";
    var ca = document.cookie.split(';');
    for (var i = 0; i < ca.length; i++) {
        var c = ca[i];
        while (c.charAt(0) == ' ') c = c.substring(1, c.length);
        if (c.indexOf(nameEQ) == 0) return c.substring(nameEQ.length, c.length);
    }
    return null;
}

function setCookie(name, value, days) {
    var expires = "";
    if (days) {
        var date = new Date();
        date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
        expires = "; expires=" + date.toUTCString();
    }
    document.cookie = name + "=" + (value || "") + expires + "; path=/";
}

function expand(e) {
    $('#loading_icon').fadeIn(200)

    order_id = e.id

    jwt_token = getCookie("jwt_token")
    rest_id = getCookie("rest_id")

    obj = {
        restaurant_id: rest_id,
    }

    if (!$('#div_' + order_id).is(':empty')) {
        $("#div_" + order_id).slideUp(function() {
            $('#loading_icon').fadeOut(200)
            $("#div_" + order_id).empty()
        })
        EXPANDED = false
        return
    }

    $.ajax({
        type: "POST",
        url: BASE_URL + "/detailed_order/" + order_id,
        dataType: "json",
        data: JSON.stringify(obj),
        contentType: "application/json",
        headers: { "X-Auth-Token": jwt_token },
        success: function(response) {
            if (response.hasOwnProperty("error")) {
                alert(response.error)
            } else if (response.hasOwnProperty("details")) {
                console.log(response)

                bill = response.details.bill

                $('#div_' + order_id).empty()
                bill.forEach(element => {
                    $('#div_' + order_id).append(`
                <div class="border-2 border-indigo-200 rounded-xl shadow-sm h-auto my-3">
                    <p class="px-3 pt-2 w-5/6 text-lg">${element.name}</p>
                    <p class="-mt-7 mr-6 float-right bg-indigo-500 px-2 rounded-md text-white">${element.quantity}</p>
                    <p class="py-1 px-3 text-sm font-semibold text-gray-600">Price: <span class="">${element.price}</span></p>
                </div>
                `)
                });

                $("#div_" + order_id).slideDown()
            } else
                alert('Unknown Response' + response)
        },
        statusCode: {
            401: function(xhr) {
                var obj = JSON.parse(xhr.responseText)
                alert(obj.error)
            }
        },
        failure: function(reponse) {
            alert(reponse)
        },
        complete: function() {
            $('#loading_icon').fadeOut(200)
        }
    });
}

function getOrderHistory(callback) {

    jwt_token = getCookie("jwt_token")
    rest_id = getCookie("rest_id")

    obj = {
        restaurant_id: rest_id,
    }

    $.ajax({
        type: "POST",
        url: BASE_URL + "/order_history",
        dataType: "json",
        data: JSON.stringify(obj),
        contentType: "application/json",
        headers: { "X-Auth-Token": jwt_token },
        success: function(response) {
            if (response.hasOwnProperty("error")) {
                alert(response.error)
            } else if (response.hasOwnProperty("order_history")) {
                console.log(response)
                order_history = response.order_history


                order_history.forEach(element => {
                    $('#order_history_container').append(`
                    <div class="xl:w-1/3 md:w-1/2 p-4">
                    <div class="bg-gray-100 p-6 rounded-lg shadow-md border-2 border-blue-100 pr-10 space-y-3">
                        <div class="pr-16 lg:pr-0">
                            <img src="../assets/user.svg" class="inline">
                            <span class="ml-2 text-purple-600">${element.name}</span>
                        </div>
                        <div class=" lg:pr-0">
                            <img src="../assets/time.svg" class="inline">
                            <span class="ml-2 text-purple-600">${element.time_and_date}</span>
                        </div>
                        <div class="slide_div py-5 hidden" id="div_${element.id}"></div>
                        <div class="lg:pr-0">
                            <img src="../assets/money.svg" class="inline">
                            <span class="ml-2 text-purple-600 text-lg">Rs.${parseInt(element.price_excluding_tax) + parseInt(element.tax)}</span>
                            <img src="../assets/up.svg" id="${element.id}" onclick="expand(this)" class="float-right transform rotate-180">
                        </div>
                    </div>
                </div>
                    `)
                });
            } else
                alert('Unknown Response' + response)
        },
        statusCode: {
            401: function(xhr) {
                var obj = JSON.parse(xhr.responseText)
                alert(obj.error)
            }
        },
        failure: function(reponse) {
            alert(reponse)
        },
        complete: function() {
            callback()
        }
    });
}

function check_if_jwt_exists() {
    jwt_token = getCookie("jwt_token")
    rest_id = getCookie("rest_id")

    if (jwt_token == null)
        window.location = "signIn.html";
    else if (rest_id == null)
        window.location = "RestroSelection.html";
}

$(document).ready(function() {
    check_if_jwt_exists()

    $('#loading_icon').fadeIn(200)
    getOrderHistory(function() {
        $('#loading_icon').fadeOut(200)
    })
});