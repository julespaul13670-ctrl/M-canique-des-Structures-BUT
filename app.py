import streamlit as st
import matplotlib.pyplot as plt
import numpy as np

# ==============================================================================
#  CLASSE MOTEUR (C'est exactement la même que ton code précédent)
# ==============================================================================
class PoutreCalculator:
    def __init__(self, longueur):
        self.L = longueur
        self.charges_ponctuelles = [] 
        self.charges_reparties = []
        self.moments_concentres = []
        self.R_gauche = 0       
        self.R_droite = 0       
        self.M_encastrement = 0 

    def ajouter_ponctuelle(self, pos, val):
        self.charges_ponctuelles.append((pos, val))

    def ajouter_repartie(self, debut, fin, val):
        self.charges_reparties.append((debut, fin, val))

    def ajouter_moment(self, pos, val):
        self.moments_concentres.append((pos, val))

    def calculer_reactions(self, type_structure):
        somme_forces = 0
        somme_moments_0 = 0 
        
        for pos, val in self.charges_ponctuelles:
            somme_forces += val
            somme_moments_0 += val * pos
            
        for debut, fin, val in self.charges_reparties:
            longueur = fin - debut
            force_res = val * longueur
            bras_levier = debut + (longueur / 2)
            somme_forces += force_res
            somme_moments_0 += force_res * bras_levier
            
        for pos, val in self.moments_concentres:
            somme_moments_0 += val 

        if type_structure == "Console (Encastrée)":
            self.R_gauche = somme_forces
            self.M_encastrement = somme_moments_0
            self.R_droite = 0
            return f"Réaction Mur: {self.R_gauche:.2f} kN | Moment Mur: {self.M_encastrement:.2f} kNm"

        elif type_structure == "Appuis Simples":
            self.R_droite = somme_moments_0 / self.L
            self.R_gauche = somme_forces - self.R_droite
            self.M_encastrement = 0 
            return f"Réaction Gauche: {self.R_gauche:.2f} kN | Réaction Droite: {self.R_droite:.2f} kN"

    def effort_tranchant(self, x):
        V = self.R_gauche
        for pos, val in self.charges_ponctuelles:
            if x > pos: V -= val
        for debut, fin, val in self.charges_reparties:
            if x > debut:
                V -= val * (min(x, fin) - debut)
        return V

    def moment_flechissant(self, x):
        M = -self.M_encastrement + (self.R_gauche * x)
        for pos, val in self.charges_ponctuelles:
            if x > pos: M -= val * (x - pos)
        for debut, fin, val in self.charges_reparties:
            if x > debut:
                len_active = min(x, fin) - debut
                force = val * len_active
                dist_centroid = debut + len_active/2
                M -= force * (x - dist_centroid)
        for pos, val in self.moments_concentres:
            if x > pos: M += val
        return M

# ==============================================================================
#  INTERFACE WEB (Streamlit)
# ==============================================================================
def main():
    st.set_page_config(page_title="RDM Calculator", page_icon="🏗️")
    
    st.title("🏗️ Calculateur RDM Universel")
    st.markdown("Créez votre poutre et visualisez les diagrammes instantanément.")

    # --- 1. CONFIGURATION ---
    st.sidebar.header("1. Configuration")
    type_struc = st.sidebar.radio("Type de structure", ["Console (Encastrée)", "Appuis Simples"])
    L = st.sidebar.number_input("Longueur (m)", value=6.0, step=0.5)

    poutre = PoutreCalculator(L)

    # --- 2. CHARGES ---
    st.sidebar.header("2. Charges")
    
    # Charges Réparties
    with st.sidebar.expander("Charges Réparties", expanded=True):
        nb_rep = st.number_input("Nombre de charges réparties", 0, 5, 0)
        for i in range(nb_rep):
            st.markdown(f"**Charge {i+1}**")
            c1, c2, c3 = st.columns(3)
            q = c1.number_input(f"Val (kN/m) #{i}", value=0.0, step=1.0)
            d = c2.number_input(f"Début (m) #{i}", value=0.0, step=0.5)
            f = c3.number_input(f"Fin (m) #{i}", value=L, step=0.5)
            if q != 0: poutre.ajouter_repartie(d, f, q)

    # Charges Ponctuelles
    with st.sidebar.expander("Charges Ponctuelles"):
        nb_ponc = st.number_input("Nombre de forces ponctuelles", 0, 5, 0)
        for i in range(nb_ponc):
            st.markdown(f"**Force {i+1}**")
            c1, c2 = st.columns(2)
            F = c1.number_input(f"Val (kN) #{i}", value=0.0, step=1.0)
            p = c2.number_input(f"Pos (m) #{i}", value=0.0, step=0.5)
            if F != 0: poutre.ajouter_ponctuelle(p, F)

    # Moments Concentrés
    with st.sidebar.expander("Moments Concentrés (Couples)"):
        nb_mom = st.number_input("Nombre de moments", 0, 5, 0)
        for i in range(nb_mom):
            st.markdown(f"**Moment {i+1}**")
            c1, c2 = st.columns(2)
            M_val = c1.number_input(f"Val (kNm) #{i}", value=0.0, step=1.0)
            p = c2.number_input(f"Pos (m) #{i}", value=0.0, step=0.5)
            if M_val != 0: poutre.ajouter_moment(p, M_val)

    # --- 3. RÉSULTATS ---
    res_text = poutre.calculer_reactions(type_struc)
    
    st.info(f"📊 RÉSULTATS : {res_text}")

    # Calculs pour graphiques
    x_vals = np.linspace(0, poutre.L, 500)
    T_vals = [poutre.effort_tranchant(x) for x in x_vals]
    M_vals = [poutre.moment_flechissant(x) for x in x_vals]

    # Graphiques avec Matplotlib
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
    plt.style.use('default') # Style plus propre pour le web

    # Tranchant
    ax1.plot(x_vals, T_vals, 'tab:blue', lw=2)
    ax1.fill_between(x_vals, T_vals, color='tab:blue', alpha=0.3)
    ax1.set_ylabel('Effort Tranchant T (kN)')
    ax1.set_title('Effort Tranchant')
    ax1.grid(True, alpha=0.3)
    ax1.axhline(0, color='black', lw=1)

    # Moment
    ax2.plot(x_vals, M_vals, 'tab:orange', lw=2)
    ax2.fill_between(x_vals, M_vals, color='tab:orange', alpha=0.3)
    ax2.set_ylabel('Mouvment Fléchissant M (kNm)')
    ax2.set_xlabel('Position x (m)')
    ax2.set_title('Mouvment Fléchissant')
    ax2.grid(True, alpha=0.3)
    ax2.axhline(0, color='black', lw=1)
    ax2.invert_yaxis()

    st.pyplot(fig)

if __name__ == "__main__":
    main()
