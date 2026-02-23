# ---
# jupyter:
#   jupytext:
#     cell_metadata_filter: -all
#     formats: ipynb,py:percent
#     notebook_metadata_filter: kernelspec,language_info,jupytext
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.1
#   kernelspec:
#     display_name: .conda
#     language: python
#     name: python3
# ---

# %% [markdown]
#

# %%
# 加载 CppHeader 扩展
# %load_ext CppHeader

# 引入 ROOT 库
import ROOT

# 启用 ROOT 的 Jupyter 扩展
# %jsroot on

# 在 Jupyter Notebook 中执行 C++ 代码
# %%cpp
#include <TCanvas.h>
TCanvas *c1 = new TCanvas;

# %%
TGraph *gEdEdxLISE(const char* inputFile)
{
  ifstream inFile(inputFile);
  if (!(inFile.is_open())) {                                                        
    cout << "Cannot find input file :" <<inputFile << endl;
    return 0;
  }   
  TGraph *gEdEdx = new TGraph;
  string str;
  for(int i=0;i<3;i++) 
    getline(inFile, str); // skip the first three lines

  // energy: MeV/u, Range: micron - do not depends on A.

  double energy, R[10], dummy;
  int n=0;
  while (getline(inFile,str) ) 
    {
        stringstream ss(str);
        ss  >> energy >> R[0] 
            >> dummy  >> R[1]
            >> dummy  >> R[2] 
            >> dummy  >> R[3] 
            >> dummy  >> R[4]  /* used for calculation */
            >> dummy  >> R[5]; 

        gEdEdx->SetPoint(n++, energy, R[4]);
    }
  inFile.close();
  cout << "Read " << n << " lines of data from the file: " << inputFile << endl;
  cout << "TGraph: x = E(MeV/u), y = dEdx(MeV/um) " << endl;
  return gEdEdx;
}



# %%


TGraph *gEdEdx = gEdEdxLISE("1H_C8H8_MwV_um.txt");



# %%
{
    gEdEdx->SetTitle("gEdEdx: dE/dx(MeV/um) vs Energy(MeV/u); MeV/u; MeV/um");
    gEdEdx->SetLineColor(kBlue);
    gEdEdx->SetMarkerColorAlpha(kRed,0.2);
    gEdEdx->Draw("AL*");
    c1->SetLogy();
    c1->SetLogx();
    c1->Draw();
}

# %%
double eloss(int A, double E0_A, double dx, TGraph *gER, TGraph *gRE)
{
    TGraph * gRE = new TGraph(gER->GetN(),gER->GetY(),gER->GetX());
    
    # int A = 12;
    # double dx = 300; // um
    # double E0_A = 200./12; // MeV
    double E0 = E0_A * A; //MeV
    double dE;
    double RE0 = gER->Eval(E0/A,0,"S");

    if(RE0 > dx) {
        double RE1 = RE0 - dx;
        double E1 = gRE->Eval(RE1,0,"S");
        dE = E0 - E1*A;
    }
    else
        dE = E0;
    cout << "Energy loss of " << E0 << " MeV 12C in "
         << dx <<" um Silicon: " << dE << endl;
}
cout<< eloss(1, 200./12, 200000, gER)<<endl;

# %%
