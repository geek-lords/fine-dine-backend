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
        url: 'https://admin-fine-dine.herokuapp.com/api/v1/photo/add',
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

function create_new_restaurant(name, description, photo_url, address, pincode, gst, callback){
    obj = {
        name:name,
        description:description,
        photo_url:photo_url,
        tax_percent:gst,
        address:address,
        pincode:pincode
    }
    $.ajax({
        type: "POST",
        url: BASE_URL+"/add_restaurant",
        data: JSON.stringify(obj),
        dataType: "json",
        contentType: "application/json",
        headers: {"X-Auth-Token": jwt_token},
        success: function (response) {
            if(response.hasOwnProperty("error")){
                alert(response.error)
            }else{
                setCookie("rest_id", response.restaurant_id, 30)  
                check_if_jwt_exists_and_go_to_admin_panel();       
            }
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
            callback()
       }
    });
}

function addRestro(e){
    e.preventDefault();
    
    $('#loading_icon').fadeIn(200)
    getURL(function(photo_url){
        res_name = $('#res-name').val()
        gst = $('#gst').val()
        addr = $('#addr').val()
        Pincode = $('#Pincode').val()
        description = $('#description').val()
    
        create_new_restaurant(res_name, description, photo_url ,addr, Pincode, gst, function(){
            $('#loading_icon').fadeOut(200)
        })
    })
}


function check_if_jwt_exists_and_go_to_admin_panel(){
    jwt_token = getCookie("jwt_token")
    rest_id = getCookie("rest_id")

    if(jwt_token==null){
        window.location = "signIn.html";
    }else if(rest_id!=null)
        window.location = "ManageOrders.html";
}

$(document).ready(function() {
    check_if_jwt_exists_and_go_to_admin_panel()
    jwt_token = getCookie("jwt_token")
});