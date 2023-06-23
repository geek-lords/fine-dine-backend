// Global variables
BASE_URL = "https://fine-dine-backend.onrender.com/api/v1/admin"

function getCookie(name) {
    var nameEQ = name + "=";
    var ca = document.cookie.split(';');
    for(var i=0;i < ca.length;i++) {
        var c = ca[i];
        while (c.charAt(0)==' ') c = c.substring(1,c.length);
        if (c.indexOf(nameEQ) == 0) return c.substring(nameEQ.length,c.length);
    }
    return null;
}

function setCookie(name,value,days) {
    var expires = "";
    if (days) {
        var date = new Date();
        date.setTime(date.getTime() + (days*24*60*60*1000));
        expires = "; expires=" + date.toUTCString();
    }
    document.cookie = name + "=" + (value || "")  + expires + "; path=/";
}


function getURL(callback){
    var logoImg = $('#upload-file').get(0).files[0];
    var Image = new FormData();
    Image.append('restaurant_photo', logoImg);
    console.log(Image)
    $.ajax({
        type: "POST",
        url: 'https://fine-dine-backend.onrender.com/api/v1/photo/add',
        data: Image,
        contentType: false,
        processData: false,
        cache: false,
        success: function(response) {
            if(response.hasOwnProperty("error")){
                alert(response.error)
            }else{
                callback(response.url) 
            }
        },
        statusCode: {
           401: function(xhr) {
               var obj = JSON.parse(xhr.responseText)
               alert(obj.error)
           }
       },
       failure: function(reponse){
           alert(reponse)
       }
    });
}

function getAllMenuItems(callback){
    jwt_token = getCookie("jwt_token")
    rest_id = getCookie("rest_id")

    $.ajax({
        type: "GET",
        url: BASE_URL+"/get_menus?restaurant_id="+rest_id,
        dataType: "json",
        contentType: "application/json",
        headers: {"X-Auth-Token": jwt_token},
        success: function (response) {
            if(response.hasOwnProperty("error")){
                alert(response.error)
            }else{
                console.log(response)  
                menu = response.menu;

                menu.forEach(element => {
                    $(`<div id="card-${element.id}" class="xl:w-1/4 md:w-1/2 p-4">
                    <div class="bg-gray-100 p-6 rounded-lg shadow-md border-2 border-blue-50">
                    <img class="h-40 rounded-xl w-full object-cover object-center mb-6" src="${element.photo_url}" alt="content">
                    <h2 class="text-lg text-gray-600 font-medium title-font mb-4">${element.name}</h2>
                    <p class="leading-relaxed text-base md:line-clamp-3">${element.description}</p><br>
                    <p class="leading-relaxed text-base">Price</p><span>Rs.${element.price}</span>
                    <button class="float-right px-4 py-2 bg-blue-600 -mt-5 rounded-md text-white remove_item" id="${element.id}">Remove</button>
                    </div>
                </div>`).insertAfter('#add_new_menu_item');  
                });
            }
        },
        statusCode: {
           401: function(xhr) {
               var obj = JSON.parse(xhr.responseText)
               alert(obj.error)
           }
       },
       failure: function(reponse){
           alert(reponse)
       },
       complete: function(){
           callback()
       }
    });
}

function addItem(e){
    $('#loading_icon').fadeIn(200)

    e.preventDefault();
    
    check_if_jwt_exists();

    getURL(function(photo_url){
        edit_name = $('#edit-name').val()
        edit_des = $('#edit-des').val()
        edit_price = $('#edit-price').val()

        jwt_token = getCookie("jwt_token")
        rest_id = getCookie("rest_id")

        obj = {
            name:edit_name,
            description:edit_des,
            photo:photo_url,
            price:edit_price,
            restaurant_id:rest_id
        }

        $.ajax({
            type: "POST",
            url: BASE_URL+"/new_menu",
            data: JSON.stringify(obj),
            dataType: "json",
            contentType: "application/json",
            headers: {"X-Auth-Token": jwt_token},
            success: function (response) {
                if(response.hasOwnProperty("error")){
                    alert(response.error)
                }else{
                    $('#edit-name').val('')    
                    $('#edit-des').val('')
                    $('#edit-price').val('')
                    $('#upload-file').val(null)

                    $(`<div id="card-${response.menu_id}" class="xl:w-1/4 md:w-1/2 p-4">
                        <div class="bg-gray-100 p-6 rounded-lg shadow-md border-2 border-blue-50">
                        <img class="h-40 rounded-xl w-full object-cover object-center mb-6" src="${photo_url}" alt="content">
                        <h2 class="text-lg text-gray-600 font-medium title-font mb-4">${edit_name}</h2>
                        <p class="leading-relaxed text-base md:line-clamp-3">${edit_des}</p><br>
                        <p class="leading-relaxed text-base">Price</p><span>Rs.${edit_price}</span>
                        <button class="float-right px-4 py-2 bg-blue-600 -mt-5 rounded-md text-white remove_item" id="${response.menu_id}">Remove</button>
                        </div>
                    </div>`).insertAfter('#add_new_menu_item');
                }
            },
            statusCode: {
               401: function(xhr) {
                   var obj = JSON.parse(xhr.responseText)
                   alert(obj.error)
               }
           },
           failure: function(reponse){
               alert(reponse)
           },complete: function(){
            $('#loading_icon').fadeOut(200)
           }
        });
    })
}

$(document).on('click', '.remove_item', function(){ 
    $('#loading_icon').fadeIn(200)

    id = this.id

    obj = {
        menu_id:id
    }

    $.ajax({
        type: "POST",
        url: BASE_URL+"/delete_menu",
        dataType: "json",
        data: JSON.stringify(obj),
        contentType: "application/json",
        headers: {"X-Auth-Token": jwt_token},
        success: function (response) {
            if(response.hasOwnProperty("error")){
                alert(response.error)
            }else if(response.hasOwnProperty("success")){
                console.log(response)  
                $("#card-"+id).fadeOut();
            }else alert('unknown response')
        },
        statusCode: {
           401: function(xhr) {
               var obj = JSON.parse(xhr.responseText)
               alert(obj.error)
           }
       },
       failure: function(response){
           alert(response)
       },
       complete: function(){
        $('#loading_icon').fadeOut(200)
       }
    });
});

function check_if_jwt_exists(){
    jwt_token = getCookie("jwt_token")
    rest_id = getCookie("rest_id")

    if(jwt_token==null)
        window.location = "signIn.html";
    else if(rest_id==null)
        window.location = "RestroSelection.html";
}

$(document).ready(function() {
    check_if_jwt_exists()

    $('#loading_icon').fadeIn(200)
    getAllMenuItems(function(){
        $('#loading_icon').fadeOut(200)
    })
});