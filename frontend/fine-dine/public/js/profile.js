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

$('#update_details_btn').on('click', function(){
    $('#loading_icon').fadeIn(200)

    f_name = $('#right_f_name').val()
    l_name = $('#right_l_name').val()
    contact = $('#right_contact').val()
    email = $('#right_email').val()

    if(f_name.trim()=="" || l_name.trim()=="" || contact.trim()=="" || email.trim()==""){
        alert("Details can't be empty")
        return
    }

    jwt_token = getCookie("jwt_token")
    rest_id = getCookie("rest_id")

    obj = {
        f_name: f_name,
        l_name: l_name,
        contact_number: contact,
        email_address: email
    }

    $.ajax({
        type: "POST",
        url: BASE_URL+"/profile",
        dataType: "json",
        data: JSON.stringify(obj),
        contentType: "application/json",
        headers: {"X-Auth-Token": jwt_token},
        success: function (response) {
            if(response.hasOwnProperty("error")){
                alert(response.error)
            }else if(response.hasOwnProperty("success")){
               
            }else 
                alert('Unknown Response'+response)
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
    
})

function getProfileDetails(){

    jwt_token = getCookie("jwt_token")
    rest_id = getCookie("rest_id")

    obj = {
        restaurant_id: rest_id,
    }

    $.ajax({
        type: "GET",
        url: BASE_URL+"/profile",
        dataType: "json",
        data: JSON.stringify(obj),
        contentType: "application/json",
        headers: {"X-Auth-Token": jwt_token},
        success: function (response) {
            if(response.hasOwnProperty("error")){
                alert(response.error)
            }else if(response.hasOwnProperty("admin_information")){
                console.log(response)
                admin_info = response.admin_information
                
                $('#left_name').html(admin_info.f_name+" "+admin_info.l_name)
                $('#right_f_name').val(admin_info.f_name)
                $('#right_l_name').val(admin_info.l_name)
                $('#right_contact').val(admin_info.contact_number)
                $('#right_email').val(admin_info.email_address)
                
                $('#update_details_btn').fadeIn()

            }else 
                alert('Unknown Response'+response)
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

function getRestDetails(callback){

    jwt_token = getCookie("jwt_token")
    rest_id = getCookie("rest_id")
    
    $.ajax({
        type: "GET",
        url: BASE_URL+"/get_restaurant",
        dataType: "json",
        contentType: "application/json",
        headers: {"X-Auth-Token": jwt_token},
        success: function (response) {
            console.log(response.restaurant_details)
            array = response.restaurant_details
            
            array.forEach(json => {
                address = json.address
                id = json.id
                rest_name = json.name
                photo_url = json.photo_url

                if(rest_id==id){
                    $('#left_rest_name').html(rest_name)
                }
        
                $('#rest_div').append(`
                <li class="p-3 bg-gray-200 rounded-xl space-y-1">
                    <a href="#" class="text-teal-600">${rest_name}</a>
                    <div class="text-gray-500 text-xs">${address}</div>
                </li>
                `)
            })
        },
        statusCode: {
           401: function(xhr) {
               var obj = JSON.parse(xhr.responseText)
               alert(obj.error)
           }
       },
       failure: function(reponse){
           console.log(reponse)
       },
       complete: function(response){
           callback()
       }
    });
}

function logOut(){
    $('#loading_icon').fadeIn(200)
    document.cookie = "jwt_token" + "=;expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/"
    document.cookie = "rest_id" + "=;expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/"
    $('#loading_icon').fadeOut(200)
    window.location.href = "signIn.html"
}


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
    getProfileDetails()
    getRestDetails(function(){
        $('#loading_icon').fadeOut(200)
    })
});