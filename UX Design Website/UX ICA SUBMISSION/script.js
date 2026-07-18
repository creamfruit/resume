document.addEventListener('DOMContentLoaded', () => {
    const sidebarToggle = document.getElementById('sidebar-toggle'); // 3 line button
    const sidebarWrapper = document.getElementById('sidebar-wrapper'); // side bar on the left
    const closeSidebarBtn = document.getElementById('close-sidebar'); // the X button
    const overlay = document.getElementById('overlay'); // the overlay that covers the main content when sidebar is open
    const mainWrapper = document.getElementById('main-wrapper'); // the main content area that adjusts when sidebar is open
    const navLinks = sidebarWrapper.querySelectorAll('.sidebar-nav ul li a'); // buttons to link to different pages

    function toggleSidebar() {
        const isExpanded = sidebarWrapper.classList.toggle('expanded');
        mainWrapper.classList.toggle('sidebar-expanded', isExpanded);

        if (window.innerWidth <= 768) {
            overlay.classList.toggle('active', isExpanded);
            document.body.classList.toggle('no-scroll', isExpanded);
        } else {
            overlay.classList.remove('active');
            document.body.classList.remove('no-scroll');
        }
    }

    sidebarToggle.addEventListener('click', toggleSidebar); // when the 3 line button is clicked, toggle the sidebar (open it)

    closeSidebarBtn.addEventListener('click', toggleSidebar); // when the X button is clicked, toggle the sidebar (close it)

    overlay.addEventListener('click', toggleSidebar); // when the overlay is clicked, toggle the sidebar (close it)

    navLinks.forEach(link => {
        link.addEventListener('click', () => {
            if (sidebarWrapper.classList.contains('expanded')) {
                toggleSidebar();
            }
        });
    });

    function handleResize() { // change size of the window
        if (window.innerWidth > 768) {
            sidebarWrapper.classList.add('expanded');
            mainWrapper.classList.add('sidebar-expanded');
            overlay.classList.remove('active');
            document.body.classList.remove('no-scroll');
        } else {
            sidebarWrapper.classList.remove('expanded');
            mainWrapper.classList.remove('sidebar-expanded');
        }
    }

    handleResize();

    window.addEventListener('resize', handleResize);
});



document.addEventListener('DOMContentLoaded', () => {
    const exitZoom = document.getElementById('exit-zoom'); // button to exit zoom mode
    const zoomedImage = document.getElementById('zoomed-image'); // the image
    const imageContainer = document.getElementById('image-container'); // the container of the image

    function exitZoomMode() {
        zoomedImage.classList.remove('zoomed');
        imageContainer.classList.remove('zoomed');
        exitZoom.style.display = 'none'; // hide the exit zoom button
    }
    exitZoom.addEventListener('click', exitZoomMode); // when the exit zoom button is clicked, exit zoom mode
    const images = document.querySelectorAll('.image-half img'); // all the images in the image half class
    images.forEach(image => {
        image.addEventListener('click', () => {
            zoomedImage.src = image.src; // set the zoomed image source to the clicked image source
            zoomedImage.classList.add('zoomed'); // add the zoomed class to the zoom
            imageContainer.classList.add('zoomed'); // add the zoomed class to the image container
            exitZoom.style.display = 'block'; // show the exit zoom button
        });
    });  
});

/*Response for Apply!!*/
document.addEventListener('DOMContentLoaded', function () {
  const form = document.getElementById('apply-form');
  
  form.addEventListener('submit', function (e) {
    e.preventDefault(); // stop page reload

    // Grab the form data
    const formData = new FormData(form);
    const params = new URLSearchParams(formData).toString();

    // Redirect to response page with query string
    window.location.href = 'response.html?' + params;
  });
});
