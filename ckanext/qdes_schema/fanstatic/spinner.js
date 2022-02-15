jQuery(document).ready(function () {
    var $loaderEl = $('.loader');
    $(window).on('load', function () {
        removeLoader();
    });
    function removeLoader() {
        $loaderEl.fadeOut(500, function () {
            // fadeOut complete. Remove the loading div
            $loaderEl.remove(); //makes page more lightweight
        });
    }
});
