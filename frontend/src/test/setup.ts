import "@testing-library/jest-dom/vitest"

// jsdom's scrollIntoView throws "Not implemented"
Element.prototype.scrollIntoView = () => {}
