// Global variables
BASE_URL = "https://fine-dine-backend.onrender.com/api/v1/admin"

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

function get_admin_restaurants(jwt_token, callback) {
    $.ajax({
        type: "GET",
        url: BASE_URL + "/get_restaurant",
        dataType: "json",
        contentType: "application/json",
        headers: { "X-Auth-Token": jwt_token },
        success: function(response) {
            console.log(response.restaurant_details)
            array = response.restaurant_details

            array.forEach(json => {
                address = json.address
                id = json.id
                rest_name = json.name
                photo_url = json.photo_url

                $('#add_rest').append(`
                <div id="${id}" class="restaurant w-auto h-auto border-2 border-gray-300 my-3 mx-6 rounded-xl flex">
                    <div class="w-20 h-20 rounded-md m-3 bg-black flex-none"> <img class="w-20 h-20 object-fill rounded-md" src="${photo_url}"> </div>
                    <div class="m-2 w-auto h-auto">
                        <span class="text-2xl text-gray-700 font-medium">${rest_name}</span>
                        <p class="text-gray-400 text-sm">${address}</p>
                    </div>
                </div>
                `)
            })
        },
        statusCode: {
            401: function(xhr) {
                var obj = JSON.parse(xhr.responseText)
                alert(obj.error)
            }
        },
        failure: function(reponse) {
            console.log(reponse)
        },
        complete: function() {
            callback()
        }
    });
}

function check_if_jwt_exists_and_go_to_admin_panel() {
    jwt_token = getCookie("jwt_token")
    rest_id = getCookie("rest_id")

    if (jwt_token == null) {
        window.location = "signIn.html";
    } else if (rest_id != null)
        window.location = "ManageOrders.html";
}

// On restaurant selection
$('body').on('click', '.restaurant', function() {
    id = this.id
    if (id == null || id == "") {
        alert("rest_id null")
        return
    }
    setCookie("rest_id", id, 30)
    check_if_jwt_exists_and_go_to_admin_panel();
});


$(document).ready(function() {
    check_if_jwt_exists_and_go_to_admin_panel()
    jwt_token = getCookie("jwt_token")
    console.log("No rest id. jwt_token:\n" + jwt_token)

    $('#loading_icon').fadeIn(200)
    get_admin_restaurants(jwt_token, function() {
        $('#loading_icon').fadeOut(200)
    })
});