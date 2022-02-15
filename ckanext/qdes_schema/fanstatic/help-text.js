(function ($) {
    $(document).ready(function () {
        /**
         * Setup position of help texts.
         */
        var $formGroup = $('.form-group');
        var $displayGroupTooltips = $('.qdes-display-group-help-text');
        var $subHeadingTooltips = $('.qdes-sub-heading-help-text');

        $formGroup.each(function () {
            var $helpTextEl = $(this).find('.qdes-help-text');
            var $labelEl = $(this).find('> label');

            if ($helpTextEl.length > 0) {
                $labelEl.after($helpTextEl);
            }
        });

        $displayGroupTooltips.each(function () {
            var $accordionTitleBtn = $(this).closest('.display-group-status').find('.acc-heading > label .title');
            $accordionTitleBtn.after($(this));
        });

        $subHeadingTooltips.each(function () {
            var $headingEl = $(this).closest('.form-group').prev();
            if ($headingEl.prop('tagName') === 'H3' || $headingEl.prop('tagName') === 'H2') {
                $headingEl.append($(this));
            }
        });

        // Init bootstrap tooltip.
        $('body').tooltip({
            placement: 'right',
            selector: '.help-text',
            container: 'body'
        });
    });
})(jQuery)
