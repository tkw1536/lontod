(function () {
    /**
     * Find RDFa resource values associated with a given property.
     *
     * @param {Element} element
     *   The element to start the search in. 
     * @param {string|null} currentAbout
     *   The current about attribute value.
     * @param {string} findAbout
     *   The IRI to find something about.
     * @param {string} findProperty 
     *   The property to find something about.
     * 
     * @returns {Generator<string, void, unknown>}
     *   Yields the found resources, if any.
     */
    function* getResourceValue(element, currentAbout, findAbout, findProperty) {
        const about = element.getAttribute('about') ?? currentAbout;

        const propertyAttribute = element.getAttribute('property');
        const resourceAttribute = element.getAttribute('resource');
        if (about === findAbout && propertyAttribute === findProperty && typeof resourceAttribute === 'string') {
            yield resourceAttribute;
        }

        for (const child of element.children) {
            if (child.nodeType !== Node.ELEMENT_NODE) {
                continue;
            }
            yield* getResourceValue(child, about, findAbout, findProperty);
        }
    }


    // get the current URL
    const iri = document.documentElement.getAttribute('about');
    if (iri === null) {
        return;
    }

    // find any version IRIs
    const versionIRI = getResourceValue(document.documentElement, null, iri, 'http://www.w3.org/2002/07/owl#versionIRI').next().value;
    const theIRI = typeof versionIRI === 'string' ? versionIRI : iri;

    // check if we have the same origin
    if (new URL(theIRI, location.toString()).origin !== location.origin) {
        console.warn("Found a canonical URL, but cannot set it because of different origin. ", theIRI);
        return;
    }

    // and replace the state
    window.history.replaceState(null, '', theIRI);
})();
