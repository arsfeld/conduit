/* -*- Mode: C; c-basic-offset: 4 -*- */
#include <pygobject.h>

void py_evolution_register_classes(PyObject *d);
extern PyMethodDef py_evolution_functions[];

DL_EXPORT(void)
init_evolution(void)
{
    PyObject *m, *d;

    /* perform any initialisation required by the library here */
	init_pygobject();
	//init();
	
    m = Py_InitModule("_evolution", py_evolution_functions);
    d = PyModule_GetDict(m);
    
    /* add anything else to the module dictionary (such as constants) */
    py_evolution_register_classes(d);
    
    if (PyErr_Occurred())
        Py_FatalError("could not initialise module _evolution");
}
