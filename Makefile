astrofit.so: astrofit.f90
	f2py3 -m astrofit -c $^

clean:
	rm -f *.so

