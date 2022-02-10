jQuery(document).ready(function () {

    $(document).on('load', function () {
        setTimeout(removeLoader, 2000); //wait for page load PLUS two seconds.
    });
    
    function removeLoader() {
        $("#loader").fadeOut('slow', function () {
            // fadeOut complete. Remove the loading div
            $("#loader").remove(); //makes page more lightweight 
        });
    }
});