g++ -Iinclude -o runPro src/globals.cpp src/function.cpp src/sekeguchi_angle_all.cpp `root-config --cflags --glibs`
# g++ -Iinclude -o runPro src/globals.cpp src/function.cpp src/compare_theory_protonTrans.cpp `root-config --cflags --glibs`
./runPro


g++ -Iinclude -o runPro src/globals.cpp src/function.cpp src/plot_energyPeru_thetalab.cpp `root-config --cflags --glibs`
./runPro


g++ -Iinclude -o runPro src/globals.cpp src/function.cpp src/set_scintilattor.cpp `root-config --cflags --glibs`
./runPro


g++ -Iinclude -o runPro src/globals.cpp src/function.cpp src/ratio_2c_proton.cpp `root-config --cflags --glibs`
./runPro

g++ -Iinclude -o runPro src/globals.cpp src/function.cpp src/R_LRUD.cpp `root-config --cflags --glibs`
./runPro

