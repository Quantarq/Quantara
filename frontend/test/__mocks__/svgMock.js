import React from 'react';

const SvgMock = React.forwardRef((props, ref) => <span ref={ref} {...props} />);

export const ReactComponent = SvgMock;
export default SvgMock;
