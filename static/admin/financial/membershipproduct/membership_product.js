document.addEventListener("DOMContentLoaded", function() {
    var frequencyField = document.getElementById('id_frequency');
    var customFrequencyInline = document.getElementById('membershipcustomfrequency-group');
    if (frequencyField.value === 'custom') {
        //console.log("(1) Is block")
        customFrequencyInline.style.display = 'block';
    } else {
        //console.log("(1) Is none")
        customFrequencyInline.style.display = 'none';
    }
    frequencyField.addEventListener('change', function() {
        var selectedValue = this.value;
        if (selectedValue === 'custom') {
            //console.log("(2) Is block")
            customFrequencyInline.style.display = 'block';
        } else {
            //console.log("(2) Is none")
            customFrequencyInline.style.display = 'none';
        }
    });
});
