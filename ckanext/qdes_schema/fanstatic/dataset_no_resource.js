jQuery(document).ready(function () {
    jQuery('button[name="save_record"]').on('click', function (e) {
        e.preventDefault();
        jQuery('input[name="_ckan_phase"]').remove();
        jQuery(this).closest('form').submit();
    });
});
