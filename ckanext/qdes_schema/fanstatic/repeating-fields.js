jQuery(document).ready(function () {
    'use strict';

    jQuery('.repeating-field').repeater({

        show: function () {
            jQuery(this).show();
        },
        hide: function (deleteElement) {
            if(confirm('Are you sure you want to remove this item?')) {
                jQuery(this).find('.form-control').val('');
                jQuery(this).hide(deleteElement);

                // Trigger blur event to regenerate the field value.
                jQuery('.repeating-field .form-control').blur();
            }
        },
        ready: function (setIndexes) {

        },
        isFirstItemUndeletable: true
    });

    function collate_inputs(repeater_id, target_field_id, field_type) {
        var collated_values = [];

        jQuery('#' + repeater_id + ' ' + field_type + '.form-control').each(function() {
            var value = jQuery(this).val();

            if (value.trim().length > 0) {
                collated_values.push(jQuery(this).val());
            }
        });

        if (collated_values.length > 0) {
            jQuery('#' + target_field_id).val(JSON.stringify(collated_values));
        }
        else {
            jQuery('#' + target_field_id).val('');
        }
    }

    jQuery(document).on('blur', ".repeating-field .form-control", function() {
        var repeater_id = jQuery(this).attr('id').replace('field-item-', '') + '-repeater';
        var target_field_id = jQuery(this).attr('id').replace('-item-', '-');
        var field_type = jQuery('#' + repeater_id).data('field-type');

        collate_inputs(repeater_id, target_field_id, field_type);
    });

});
