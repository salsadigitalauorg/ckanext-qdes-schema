jQuery(document).ready(function () {
    data_quality_standard = jQuery('#data_quality_standard').val() || '{}'
    data_quality_standard = data_quality_standard == '{}' ? {calculated_quality_measure: 0} : JSON.parse(data_quality_standard)

    // Set on click event for checkboxes
    jQuery('.calculated-quality-measure > .collapsing-section').find('input[type=radio]').on('click', function () {
        calculate_quality_measure(jQuery(this).closest('.collapsing-section'))
    });

    // Run initial calculation of checkboxes on page load
    jQuery('.calculated-quality-measure > .collapsing-section').each(function () {
        calculate_quality_measure(jQuery(this))
    })

    function calculate_quality_measure(element) {
        if (! data_quality_standard.hasOwnProperty(element.data('field_name'))) {
            data_quality_standard[element.data('field_name')] = {}
        }

        subfield = data_quality_standard[element.data('field_name')]
        subfield['score'] = 0
        element.find('input[type=radio]:checked').each(function () {
            radio = this
            score = radio.value == "YES" ? 1 : 0
            subfield[radio.name] = score 
            subfield['score'] = subfield['score'] + score
        });
        
        element.closest('article.calculated-quality-measure').find('.score').text("(" + subfield['score'] + ")").data('score', subfield['score'])
        calculated_quality_measure_score()
    }

    function calculated_quality_measure_score() {
        total_score = 0
        score = jQuery('.calculated-quality-measure').find('.score').each(function () {
            total_score = jQuery(this).data('score') + total_score
        })
        jQuery('#calculated_quality_measure_score').text(total_score)
        data_quality_standard['calculated_quality_measure'] = total_score
        jQuery('#data_quality_standard').val(JSON.stringify(data_quality_standard))

    }



});
