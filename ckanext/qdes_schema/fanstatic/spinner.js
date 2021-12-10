jQuery(document).ready(function () {
    $('body').append('<div id="loadingDiv" class="spinner-border" role="status"> <span class="sr-only">Loading...</span></div>');
    $(window).on('load', function () {
        setTimeout(removeLoader, 2000); //wait for page load PLUS two seconds.
    });
    function removeLoader() {
        $("#loadingDiv").fadeOut(500, function () {
            // fadeOut complete. Remove the loading div
            $("#loadingDiv").remove(); //makes page more lightweight 
        });
    }
});