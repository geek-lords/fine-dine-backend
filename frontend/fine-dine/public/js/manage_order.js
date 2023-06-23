// Global variables
BASE_URL = "https://fine-dine-backend.onrender.com/api/v1/admin"
NEW_ORDERS_CLICKED = true

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

function newItemChecked(e) {
    $('#loading_icon').fadeIn(200)
    var menu_id = e.id

    jwt_token = getCookie("jwt_token")
    rest_id = getCookie("rest_id")
    obj = {
        restaurant_id: rest_id
    }
    $.ajax({
        type: "POST",
        url: BASE_URL + "/delivered/" + menu_id,
        data: JSON.stringify(obj),
        dataType: "json",
        contentType: "application/json",
        headers: { "X-Auth-Token": jwt_token },
        success: function(response) {
            console.log(response)
            if (response.hasOwnProperty("error")) {
                alert(response.error)
            } else if (response.hasOwnProperty("success")) {
                parent = $("#item_" + menu_id).parent()
                $("#item_" + menu_id).remove();
            } else alert('Unknown response')
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

function get_payment_status(id) {
    switch (id) {
        case "0":
            return "Paid";
        case "1":
            return "Pending";
        case "2":
            return "Invalid";
        case "3":
            return "Failed";
        case "4":
            return "Not Paid";
        default:
            return "Unknown";
    }
}

$('#new_order_btn').click(function() {
    NEW_ORDERS_CLICKED = true
    $('.new_order_cards').show()
    $('.served_order_cards').remove()
})

$('#served_order_btn').on('click', function() {
    NEW_ORDERS_CLICKED = false
    $('.new_order_cards').hide()
    $('.served_order_cards').remove()
    get_served_orders()
})

function get_new_orders() {

    jwt_token = getCookie("jwt_token")
    rest_id = getCookie("rest_id")
    obj = {
        restaurant_id: rest_id
    }
    $.ajax({
        type: "POST",
        url: BASE_URL + "/new_orders",
        data: JSON.stringify(obj),
        dataType: "json",
        contentType: "application/json",
        headers: { "X-Auth-Token": jwt_token },
        success: function(response) {
            if (response.hasOwnProperty("error")) {
                alert(response.error)
            } else if (response.hasOwnProperty("new_orders")) {
                console.log(response)
                tables = response["new_orders"]

                $('.new_order_cards').remove()
                var count = 0
                for (let key in tables) {
                    if (tables.hasOwnProperty(key)) {
                        count++
                        table = key
                        var val = tables[key];
                        var username = val["users.name"];
                        var orders = val["orders"];
                        $('#card_container').append(`
                    <div class="xl:w-1/3 md:w-1/2 p-4 new_order_cards">
                        <div class="bg-gray-100 p-6 rounded-lg shadow-md border-2">
                            <h2 class="text-lg text-gray-600 font-medium title-font mb-4 pr-16 lg:pr-0">${table}</h2>
                            <p class="text-xs mt-2">Cust Name:<span class="ml-2 text-purple-600">${username}</span></p>
                            <div id="${table.replace(/\s/g, "")}_menu_div" class="">                                
                            </div>
                        </div>
                    </div>
                    `)
                        orders.forEach(element => {
                            $(`#${table.replace(/\s/g, "")}_menu_div`).append(`
                       <div id="item_${element["id"]}" class="border-2 border-indigo-200 rounded-xl shadow-sm h-auto flex my-3">
                       <p class="p-3 w-5/6">${element["name"]}</p>
                       <input id="${element["id"]}" onclick="newItemChecked(this)" type="checkbox" class="mt-4 mr-5">
                       <p class="bg-blue-500 rounded-r-xl text-white p-3">${element["quantity"]}</p>
                       </div>
                       `)
                        });

                        console.log("new orders clicked:" + NEW_ORDERS_CLICKED)
                        if (!NEW_ORDERS_CLICKED) $('.new_order_cards').hide()
                    }
                }
                $('#order-count').html(count)
            } else alert('Unknown response')
        },
        statusCode: {
            401: function(xhr) {
                var obj = JSON.parse(xhr.responseText)
                alert(obj.error)
            }
        },
        failure: function(reponse) {
            alert(reponse)
        }
    });
}

function get_served_orders() {
    $('#loading_icon').fadeIn(200)

    jwt_token = getCookie("jwt_token")
    rest_id = getCookie("rest_id")

    obj = {
        restaurant_id: rest_id
    }
    $.ajax({
        type: "POST",
        url: BASE_URL + "/recent_orders",
        data: JSON.stringify(obj),
        dataType: "json",
        contentType: "application/json",
        headers: { "X-Auth-Token": jwt_token },
        success: function(response) {
            if (response.hasOwnProperty("error")) {
                alert(response.error)
            } else if (response.hasOwnProperty("recent_orders")) {
                console.log(response)

                tables = response["recent_orders"]

                for (let key in tables) {
                    if (tables.hasOwnProperty(key)) {
                        var val = tables[key];
                        table = key
                        var username = val["name"];
                        var orders = val["orders"];

                        $('#card_container').append(`
                    <div class="xl:w-1/3 md:w-1/2 p-4 served_order_cards">
                        <div class="bg-gray-100 p-6 rounded-lg shadow-md border-2">
                            <h2 class="text-base text-gray-600 font-medium title-font pr-16 lg:pr-0">${table}</h2>
                            <p class="-mt-7 -mr-5 float-right p-1 rounded-md text-xs ${orders[0]["payment_status"]=="0"?"border-2 border-green-300 text-green-400":"border-2 border-red-300 text-red-400"}">${get_payment_status(orders[0]["payment_status"])}</p>
                            <p class="text-xs mt-2">Cust Name:<span class="ml-2 text-purple-600">${username}</span></p>
                            <div id="${table.replace(/\s/g, "")}_served_menu_div" class="">                                
                            </div>
                        </div>
                    </div>
                    `)
                        orders.forEach(element => {
                            $(`#${table.replace(/\s/g, "")}_served_menu_div`).append(`
                       <div class="border-2 border-indigo-200 rounded-xl shadow-sm h-auto flex my-2">
                       <p class="p-3 w-5/6">${element["menu.name"]}</p>
                       <p class="m-3 float-right align-middle bg-indigo-500 px-2 rounded-md text-white">${element["quantity"]}</p>
                       `)
                        });


                    }
                }

            } else alert('Unknown response')
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
    get_new_orders()
    $('#loading_icon').fadeOut(200)
    setInterval(function() {
        get_new_orders()
    }, 5000);

});