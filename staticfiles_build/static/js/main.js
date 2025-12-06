// Main JavaScript functionality

$(document).ready(function() {
    // Initialize DataTables if present
    if ($.fn.DataTable) {
        $('.table').DataTable({
            responsive: true,
            language: {
                url: '//cdn.datatables.net/plug-ins/1.11.5/i18n/French.json'
            }
        });
    }
    
    // Initialize tooltips
    if ($.fn.tooltip) {
        $('[data-toggle="tooltip"]').tooltip();
    }
    
    // Initialize popovers
    if ($.fn.popover) {
        $('[data-toggle="popover"]').popover();
    }
    
    // Form validation
    $('.needs-validation').on('submit', function(e) {
        if (!this.checkValidity()) {
            e.preventDefault();
            e.stopPropagation();
        }
        $(this).addClass('was-validated');
    });
    
    // Auto-hide alerts after 5 seconds
    $('.alert').delay(5000).fadeOut();
});

// Utility functions
function showAlert(message, type = 'info') {
    const alertHtml = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="close" data-dismiss="alert">
                <span>&times;</span>
            </button>
        </div>
    `;
    $('#main-content').prepend(alertHtml);
}