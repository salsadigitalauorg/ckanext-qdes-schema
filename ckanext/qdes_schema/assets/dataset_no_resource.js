jQuery(document).ready(function () {
    jQuery('button[name="save_record"]').on("click", function (e) {
        e.preventDefault();
        if (jQuery('input[name="pkg_name"]').val().length > 0) {
            jQuery('input[name="_ckan_phase"]').val("save_record");
        } else {
            jQuery('input[name="_ckan_phase"]').remove();
        }
        jQuery(this).closest("form").submit();
    });
});
