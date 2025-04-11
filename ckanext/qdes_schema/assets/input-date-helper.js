(function ($) {
    $(document).ready(function () {
        /**
         * Setup clear button on input[type=date] elements.
         */
        var $clearEl = $('.clear-btn');
        var eventF = function ($el) {
            if ($el.val().length > 0) {
                $el.parent().addClass('show-clear-btn');
            } else {
                $el.parent().removeClass('show-clear-btn');
            }
        }

        $clearEl.each(function () {
            var $inputEl = $(this).parent().find('input');

            if ($inputEl.attr('type') === 'date') {
                $inputEl.change(function () {
                    eventF($(this));
                });

                $inputEl.change();
            } else {
                $inputEl.keyup(function () {
                    eventF($(this));
                });
                $inputEl.keyup();
            }
        });

        // Listen to clear button.
        $clearEl.click(function () {
            var $inputEl = $(this).parent().find('input');
            $inputEl.val("");

            if ($inputEl.attr('type') === 'date') {
                $inputEl.change();
            }
            else {
                $inputEl.keyup();
            }
        });
    });
})(jQuery)
