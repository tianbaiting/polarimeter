# g++ -Iinclude -o runPro src/globals.cpp src/function.cpp src/plot_energyPeru_thetalab.cpp `root-config --cflags --glibs`
# # g++ -Iinclude -o runPro src/globals.cpp src/function.cpp src/compare_theory_protonTrans.cpp `root-config --cflags --glibs`
# ./runPro

g++ -Iinclude -o runPro src/globals.cpp src/function.cpp src/set_scintilattor.cpp `root-config --cflags --glibs`
./runPro