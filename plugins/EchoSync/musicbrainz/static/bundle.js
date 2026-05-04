//#region node_modules/svelte/src/internal/disclose-version.js
typeof window < "u" && ((window.__svelte ??= {}).v ??= /* @__PURE__ */ new Set()).add("5");
//#endregion
//#region node_modules/svelte/src/internal/flags/index.js
var e = !1, t = !1;
function n() {
	t = !0;
}
//#endregion
//#region node_modules/svelte/src/internal/flags/legacy.js
n();
//#endregion
//#region node_modules/svelte/src/constants.js
var r = {}, i = Symbol(), a = "http://www.w3.org/1999/xhtml", o = Array.isArray, s = Array.prototype.indexOf, c = Array.prototype.includes, l = Array.from, u = Object.keys, d = Object.defineProperty, f = Object.getOwnPropertyDescriptor, p = Object.getOwnPropertyDescriptors, m = Object.prototype, h = Array.prototype, g = Object.getPrototypeOf, _ = Object.isExtensible, v = () => {};
function y(e) {
	return e();
}
function b(e) {
	for (var t = 0; t < e.length; t++) e[t]();
}
function x() {
	var e, t;
	return {
		promise: new Promise((n, r) => {
			e = n, t = r;
		}),
		resolve: e,
		reject: t
	};
}
var S = 1024, C = 2048, w = 4096, ee = 8192, te = 16384, ne = 32768, re = 1 << 25, ie = 65536, ae = 1 << 19, oe = 1 << 20, se = 1 << 25, ce = 65536, le = 1 << 21, ue = 1 << 22, de = 1 << 23, fe = Symbol("$state"), pe = Symbol("legacy props"), me = Symbol(""), T = new class extends Error {
	name = "StaleReactionError";
	message = "The reaction that called `getAbortSignal()` was re-run or destroyed";
}(), he = !!globalThis.document?.contentType && /* @__PURE__ */ globalThis.document.contentType.includes("xml");
function ge(e) {
	throw Error("https://svelte.dev/e/lifecycle_outside_component");
}
//#endregion
//#region node_modules/svelte/src/internal/client/errors.js
function _e() {
	throw Error("https://svelte.dev/e/async_derived_orphan");
}
function ve(e, t, n) {
	throw Error("https://svelte.dev/e/each_key_duplicate");
}
function ye(e) {
	throw Error("https://svelte.dev/e/effect_in_teardown");
}
function be() {
	throw Error("https://svelte.dev/e/effect_in_unowned_derived");
}
function xe(e) {
	throw Error("https://svelte.dev/e/effect_orphan");
}
function Se() {
	throw Error("https://svelte.dev/e/effect_update_depth_exceeded");
}
function Ce() {
	throw Error("https://svelte.dev/e/hydration_failed");
}
function we(e) {
	throw Error("https://svelte.dev/e/props_invalid_value");
}
function Te() {
	throw Error("https://svelte.dev/e/state_descriptors_fixed");
}
function Ee() {
	throw Error("https://svelte.dev/e/state_prototype_fixed");
}
function De() {
	throw Error("https://svelte.dev/e/state_unsafe_mutation");
}
function Oe() {
	throw Error("https://svelte.dev/e/svelte_boundary_reset_onerror");
}
function ke() {
	console.warn("https://svelte.dev/e/derived_inert");
}
function Ae(e) {
	console.warn("https://svelte.dev/e/hydration_mismatch");
}
function je() {
	console.warn("https://svelte.dev/e/svelte_boundary_reset_noop");
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/hydration.js
var E = !1;
function Me(e) {
	E = e;
}
var D;
function O(e) {
	if (e === null) throw Ae(), r;
	return D = e;
}
function Ne() {
	return O(/* @__PURE__ */ en(D));
}
function k(e) {
	if (E) {
		if (/* @__PURE__ */ en(D) !== null) throw Ae(), r;
		D = e;
	}
}
function Pe(e = 1) {
	if (E) {
		for (var t = e, n = D; t--;) n = /* @__PURE__ */ en(n);
		D = n;
	}
}
function Fe(e = !0) {
	for (var t = 0, n = D;;) {
		if (n.nodeType === 8) {
			var r = n.data;
			if (r === "]") {
				if (t === 0) return n;
				--t;
			} else (r === "[" || r === "[!" || r[0] === "[" && !isNaN(Number(r.slice(1)))) && (t += 1);
		}
		var i = /* @__PURE__ */ en(n);
		e && n.remove(), n = i;
	}
}
function Ie(e) {
	if (!e || e.nodeType !== 8) throw Ae(), r;
	return e.data;
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/equality.js
function Le(e) {
	return e === this.v;
}
function Re(e, t) {
	return e == e ? e !== t || typeof e == "object" && !!e || typeof e == "function" : t == t;
}
function ze(e) {
	return !Re(e, this.v);
}
//#endregion
//#region node_modules/svelte/src/internal/client/context.js
var A = null;
function Be(e) {
	A = e;
}
function Ve(e, n = !1, r) {
	A = {
		p: A,
		i: !1,
		c: null,
		e: null,
		s: e,
		x: null,
		r: W,
		l: t && !n ? {
			s: null,
			u: null,
			$: []
		} : null
	};
}
function He(e) {
	var t = A, n = t.e;
	if (n !== null) {
		t.e = null;
		for (var r of n) _n(r);
	}
	return e !== void 0 && (t.x = e), t.i = !0, A = t.p, e ?? {};
}
function Ue() {
	return !t || A !== null && A.l === null;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/task.js
var We = [];
function Ge() {
	var e = We;
	We = [], b(e);
}
function Ke(e) {
	if (We.length === 0 && !ot) {
		var t = We;
		queueMicrotask(() => {
			t === We && Ge();
		});
	}
	We.push(e);
}
function qe() {
	for (; We.length > 0;) Ge();
}
function Je(e) {
	var t = W;
	if (t === null) return V.f |= de, e;
	if (!(t.f & 32768) && !(t.f & 4)) throw e;
	Ye(e, t);
}
function Ye(e, t) {
	for (; t !== null;) {
		if (t.f & 128) {
			if (!(t.f & 32768)) throw e;
			try {
				t.b.error(e);
				return;
			} catch (t) {
				e = t;
			}
		}
		t = t.parent;
	}
	throw e;
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/status.js
var Xe = ~(C | w | S);
function j(e, t) {
	e.f = e.f & Xe | t;
}
function Ze(e) {
	e.f & 512 || e.deps === null ? j(e, S) : j(e, w);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/utils.js
function Qe(e) {
	if (e !== null) for (let t of e) !(t.f & 2) || !(t.f & 65536) || (t.f ^= ce, Qe(t.deps));
}
function $e(e, t, n) {
	e.f & 2048 ? t.add(e) : e.f & 4096 && n.add(e), Qe(e.deps), j(e, S);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/store.js
var et = !1, tt = !1;
function nt(e) {
	var t = tt;
	try {
		return tt = !1, [e(), tt];
	} finally {
		tt = t;
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/batch.js
var rt = /* @__PURE__ */ new Set(), M = null, it = null, N = null, at = null, ot = !1, st = !1, ct = null, lt = null, ut = 0, dt = 1, ft = class t {
	id = dt++;
	current = /* @__PURE__ */ new Map();
	previous = /* @__PURE__ */ new Map();
	#e = /* @__PURE__ */ new Set();
	#t = /* @__PURE__ */ new Set();
	#n = /* @__PURE__ */ new Set();
	#r = /* @__PURE__ */ new Map();
	#i = /* @__PURE__ */ new Map();
	#a = null;
	#o = [];
	#s = [];
	#c = /* @__PURE__ */ new Set();
	#l = /* @__PURE__ */ new Set();
	#u = /* @__PURE__ */ new Map();
	#d = /* @__PURE__ */ new Set();
	is_fork = !1;
	#f = !1;
	#p = /* @__PURE__ */ new Set();
	#m() {
		return this.is_fork || this.#i.size > 0;
	}
	#h() {
		for (let n of this.#p) for (let r of n.#i.keys()) {
			for (var e = !1, t = r; t.parent !== null;) {
				if (this.#u.has(t)) {
					e = !0;
					break;
				}
				t = t.parent;
			}
			if (!e) return !0;
		}
		return !1;
	}
	skip_effect(e) {
		this.#u.has(e) || this.#u.set(e, {
			d: [],
			m: []
		}), this.#d.delete(e);
	}
	unskip_effect(e, t = (e) => this.schedule(e)) {
		var n = this.#u.get(e);
		if (n) {
			this.#u.delete(e);
			for (var r of n.d) j(r, C), t(r);
			for (r of n.m) j(r, w), t(r);
		}
		this.#d.add(e);
	}
	#g() {
		if (ut++ > 1e3 && (rt.delete(this), mt()), !this.#m()) {
			for (let e of this.#c) this.#l.delete(e), j(e, C), this.schedule(e);
			for (let e of this.#l) j(e, w), this.schedule(e);
		}
		let n = this.#o;
		this.#o = [], this.apply();
		var r = ct = [], i = [], a = lt = [];
		for (let e of n) try {
			this.#_(e, r, i);
		} catch (t) {
			throw xt(e), t;
		}
		if (M = null, a.length > 0) {
			var o = t.ensure();
			for (let e of a) o.schedule(e);
		}
		if (ct = null, lt = null, this.#m() || this.#h()) {
			this.#v(i), this.#v(r);
			for (let [e, t] of this.#u) bt(e, t);
		} else {
			this.#r.size === 0 && rt.delete(this), this.#c.clear(), this.#l.clear();
			for (let e of this.#e) e(this);
			this.#e.clear(), it = this, gt(i), gt(r), it = null, this.#a?.resolve();
		}
		var s = M;
		if (this.#o.length > 0) {
			let e = s ??= this;
			e.#o.push(...this.#o.filter((t) => !e.#o.includes(t)));
		}
		s !== null && (rt.add(s), s.#g()), e && !rt.has(this) && this.#y();
	}
	#_(t, n, r) {
		t.f ^= S;
		for (var i = t.first; i !== null;) {
			var a = i.f, o = (a & 96) != 0;
			if (!(o && a & 1024 || a & 8192 || this.#u.has(i)) && i.fn !== null) {
				o ? i.f ^= S : a & 4 ? n.push(i) : e && a & 16777224 ? r.push(i) : qn(i) && (a & 16 && this.#l.add(i), Qn(i));
				var s = i.first;
				if (s !== null) {
					i = s;
					continue;
				}
			}
			for (; i !== null;) {
				var c = i.next;
				if (c !== null) {
					i = c;
					break;
				}
				i = i.parent;
			}
		}
	}
	#v(e) {
		for (var t = 0; t < e.length; t += 1) $e(e[t], this.#c, this.#l);
	}
	capture(e, t, n = !1) {
		e.v !== i && !this.previous.has(e) && this.previous.set(e, e.v), e.f & 8388608 || (this.current.set(e, [t, n]), N?.set(e, t)), this.is_fork || (e.v = t);
	}
	activate() {
		M = this;
	}
	deactivate() {
		M = null, N = null;
	}
	flush() {
		try {
			st = !0, M = this, this.#g();
		} finally {
			ut = 0, at = null, ct = null, lt = null, st = !1, M = null, N = null, zt.clear();
		}
	}
	discard() {
		for (let e of this.#t) e(this);
		this.#t.clear(), this.#n.clear(), rt.delete(this);
	}
	register_created_effect(e) {
		this.#s.push(e);
	}
	#y() {
		for (let l of rt) {
			var e = l.id < this.id, t = [];
			for (let [r, [i, a]] of this.current) {
				if (l.current.has(r)) {
					var n = l.current.get(r)[0];
					if (e && i !== n) l.current.set(r, [i, a]);
					else continue;
				}
				t.push(r);
			}
			var r = [...l.current.keys()].filter((e) => !this.current.has(e));
			if (r.length === 0) e && l.discard();
			else if (t.length > 0) {
				if (e) for (let e of this.#d) l.unskip_effect(e, (e) => {
					e.f & 4194320 ? l.schedule(e) : l.#v([e]);
				});
				l.activate();
				var i = /* @__PURE__ */ new Set(), a = /* @__PURE__ */ new Map();
				for (var o of t) _t(o, r, i, a);
				a = /* @__PURE__ */ new Map();
				var s = [...l.current.keys()].filter((e) => this.current.has(e) ? this.current.get(e)[0] !== e : !0);
				for (let e of this.#s) !(e.f & 155648) && vt(e, s, a) && (e.f & 4194320 ? (j(e, C), l.schedule(e)) : l.#c.add(e));
				if (l.#o.length > 0) {
					l.apply();
					for (var c of l.#o) l.#_(c, [], []);
					l.#o = [];
				}
				l.deactivate();
			}
		}
		for (let e of rt) e.#p.has(this) && (e.#p.delete(this), e.#p.size === 0 && !e.#m() && (e.activate(), e.#g()));
	}
	increment(e, t) {
		let n = this.#r.get(t) ?? 0;
		if (this.#r.set(t, n + 1), e) {
			let e = this.#i.get(t) ?? 0;
			this.#i.set(t, e + 1);
		}
	}
	decrement(e, t, n) {
		let r = this.#r.get(t) ?? 0;
		if (r === 1 ? this.#r.delete(t) : this.#r.set(t, r - 1), e) {
			let e = this.#i.get(t) ?? 0;
			e === 1 ? this.#i.delete(t) : this.#i.set(t, e - 1);
		}
		this.#f || n || (this.#f = !0, Ke(() => {
			this.#f = !1, this.flush();
		}));
	}
	transfer_effects(e, t) {
		for (let t of e) this.#c.add(t);
		for (let e of t) this.#l.add(e);
		e.clear(), t.clear();
	}
	oncommit(e) {
		this.#e.add(e);
	}
	ondiscard(e) {
		this.#t.add(e);
	}
	on_fork_commit(e) {
		this.#n.add(e);
	}
	run_fork_commit_callbacks() {
		for (let e of this.#n) e(this);
		this.#n.clear();
	}
	settled() {
		return (this.#a ??= x()).promise;
	}
	static ensure() {
		if (M === null) {
			let e = M = new t();
			st || (rt.add(M), ot || Ke(() => {
				M === e && e.flush();
			}));
		}
		return M;
	}
	apply() {
		if (!e || !this.is_fork && rt.size === 1) {
			N = null;
			return;
		}
		N = /* @__PURE__ */ new Map();
		for (let [e, [t]] of this.current) N.set(e, t);
		for (let e of rt) if (!(e === this || e.is_fork)) {
			var t = !1, n = !1;
			if (e.id < this.id) for (let [r, [, i]] of e.current) i || (t ||= this.current.has(r), n ||= !this.current.has(r));
			if (t && n) this.#p.add(e);
			else for (let [t, n] of e.previous) N.has(t) || N.set(t, n);
		}
	}
	schedule(t) {
		if (at = t, t.b?.is_pending && t.f & 16777228 && !(t.f & 32768)) {
			t.b.defer_effect(t);
			return;
		}
		for (var n = t; n.parent !== null;) {
			n = n.parent;
			var r = n.f;
			if (ct !== null && n === W && (e || (V === null || !(V.f & 2)) && !et)) return;
			if (r & 96) {
				if (!(r & 1024)) return;
				n.f ^= S;
			}
		}
		this.#o.push(n);
	}
};
function pt(e) {
	var t = ot;
	ot = !0;
	try {
		var n;
		for (e && (M !== null && !M.is_fork && M.flush(), n = e());;) {
			if (qe(), M === null) return n;
			M.flush();
		}
	} finally {
		ot = t;
	}
}
function mt() {
	try {
		Se();
	} catch (e) {
		Ye(e, at);
	}
}
var ht = null;
function gt(e) {
	var t = e.length;
	if (t !== 0) {
		for (var n = 0; n < t;) {
			var r = e[n++];
			if (!(r.f & 24576) && qn(r) && (ht = /* @__PURE__ */ new Set(), Qn(r), r.deps === null && r.first === null && r.nodes === null && r.teardown === null && r.ac === null && kn(r), ht?.size > 0)) {
				zt.clear();
				for (let e of ht) {
					if (e.f & 24576) continue;
					let t = [e], n = e.parent;
					for (; n !== null;) ht.has(n) && (ht.delete(n), t.push(n)), n = n.parent;
					for (let e = t.length - 1; e >= 0; e--) {
						let n = t[e];
						n.f & 24576 || Qn(n);
					}
				}
				ht.clear();
			}
		}
		ht = null;
	}
}
function _t(e, t, n, r) {
	if (!n.has(e) && (n.add(e), e.reactions !== null)) for (let i of e.reactions) {
		let e = i.f;
		e & 2 ? _t(i, t, n, r) : e & 4194320 && !(e & 2048) && vt(i, t, r) && (j(i, C), yt(i));
	}
}
function vt(e, t, n) {
	let r = n.get(e);
	if (r !== void 0) return r;
	if (e.deps !== null) for (let r of e.deps) {
		if (c.call(t, r)) return !0;
		if (r.f & 2 && vt(r, t, n)) return n.set(r, !0), !0;
	}
	return n.set(e, !1), !1;
}
function yt(e) {
	M.schedule(e);
}
function bt(e, t) {
	if (!(e.f & 32 && e.f & 1024)) {
		e.f & 2048 ? t.d.push(e) : e.f & 4096 && t.m.push(e), j(e, S);
		for (var n = e.first; n !== null;) bt(n, t), n = n.next;
	}
}
function xt(e) {
	j(e, S);
	for (var t = e.first; t !== null;) xt(t), t = t.next;
}
//#endregion
//#region node_modules/svelte/src/reactivity/create-subscriber.js
function St(e) {
	let t = 0, n = Vt(0), r;
	return () => {
		mn() && (Y(n), Sn(() => (t === 0 && (r = X(() => e(() => Gt(n)))), t += 1, () => {
			Ke(() => {
				--t, t === 0 && (r?.(), r = void 0, Gt(n));
			});
		})));
	};
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/boundary.js
var Ct = ie | ae;
function wt(e, t, n, r) {
	new Tt(e, t, n, r);
}
var Tt = class {
	parent;
	is_pending = !1;
	transform_error;
	#e;
	#t = E ? D : null;
	#n;
	#r;
	#i;
	#a = null;
	#o = null;
	#s = null;
	#c = null;
	#l = 0;
	#u = 0;
	#d = !1;
	#f = /* @__PURE__ */ new Set();
	#p = /* @__PURE__ */ new Set();
	#m = null;
	#h = St(() => (this.#m = Vt(this.#l), () => {
		this.#m = null;
	}));
	constructor(e, t, n, r) {
		this.#e = e, this.#n = t, this.#r = (e) => {
			var t = W;
			t.b = this, t.f |= 128, n(e);
		}, this.parent = W.b, this.transform_error = r ?? this.parent?.transform_error ?? ((e) => e), this.#i = wn(() => {
			if (E) {
				let e = this.#t;
				Ne();
				let t = e.data === "[!";
				if (e.data.startsWith("[?")) {
					let t = JSON.parse(e.data.slice(2));
					this.#_(t);
				} else t ? this.#v() : this.#g();
			} else this.#y();
		}, Ct), E && (this.#e = D);
	}
	#g() {
		try {
			this.#a = z(() => this.#r(this.#e));
		} catch (e) {
			this.error(e);
		}
	}
	#_(e) {
		let t = this.#n.failed;
		t && (this.#s = z(() => {
			t(this.#e, () => e, () => () => {});
		}));
	}
	#v() {
		let e = this.#n.pending;
		e && (this.is_pending = !0, this.#o = z(() => e(this.#e)), Ke(() => {
			var e = this.#c = document.createDocumentFragment(), t = I();
			e.append(t), this.#a = this.#x(() => z(() => this.#r(t))), this.#u === 0 && (this.#e.before(e), this.#c = null, An(this.#o, () => {
				this.#o = null;
			}), this.#b(M));
		}));
	}
	#y() {
		try {
			if (this.is_pending = this.has_pending_snippet(), this.#u = 0, this.#l = 0, this.#a = z(() => {
				this.#r(this.#e);
			}), this.#u > 0) {
				var e = this.#c = document.createDocumentFragment();
				Pn(this.#a, e);
				let t = this.#n.pending;
				this.#o = z(() => t(this.#e));
			} else this.#b(M);
		} catch (e) {
			this.error(e);
		}
	}
	#b(e) {
		this.is_pending = !1, e.transfer_effects(this.#f, this.#p);
	}
	defer_effect(e) {
		$e(e, this.#f, this.#p);
	}
	is_rendered() {
		return !this.is_pending && (!this.parent || this.parent.is_rendered());
	}
	has_pending_snippet() {
		return !!this.#n.pending;
	}
	#x(e) {
		var t = W, n = V, r = A;
		zn(this.#i), U(this.#i), Be(this.#i.ctx);
		try {
			return ft.ensure(), e();
		} catch (e) {
			return Je(e), null;
		} finally {
			zn(t), U(n), Be(r);
		}
	}
	#S(e, t) {
		if (!this.has_pending_snippet()) {
			this.parent && this.parent.#S(e, t);
			return;
		}
		this.#u += e, this.#u === 0 && (this.#b(t), this.#o && An(this.#o, () => {
			this.#o = null;
		}), this.#c &&= (this.#e.before(this.#c), null));
	}
	update_pending_count(e, t) {
		this.#S(e, t), this.#l += e, !(!this.#m || this.#d) && (this.#d = !0, Ke(() => {
			this.#d = !1, this.#m && Ut(this.#m, this.#l);
		}));
	}
	get_effect_pending() {
		return this.#h(), Y(this.#m);
	}
	error(e) {
		if (!this.#n.onerror && !this.#n.failed) throw e;
		M?.is_fork ? (this.#a && M.skip_effect(this.#a), this.#o && M.skip_effect(this.#o), this.#s && M.skip_effect(this.#s), M.on_fork_commit(() => {
			this.#C(e);
		})) : this.#C(e);
	}
	#C(e) {
		this.#a &&= (B(this.#a), null), this.#o &&= (B(this.#o), null), this.#s &&= (B(this.#s), null), E && (O(this.#t), Pe(), O(Fe()));
		var t = this.#n.onerror;
		let n = this.#n.failed;
		var r = !1, i = !1;
		let a = () => {
			if (r) {
				je();
				return;
			}
			r = !0, i && Oe(), this.#s !== null && An(this.#s, () => {
				this.#s = null;
			}), this.#x(() => {
				this.#y();
			});
		}, o = (e) => {
			try {
				i = !0, t?.(e, a), i = !1;
			} catch (e) {
				Ye(e, this.#i && this.#i.parent);
			}
			n && (this.#s = this.#x(() => {
				try {
					return z(() => {
						var t = W;
						t.b = this, t.f |= 128, n(this.#e, () => e, () => a);
					});
				} catch (e) {
					return Ye(e, this.#i.parent), null;
				}
			}));
		};
		Ke(() => {
			var t;
			try {
				t = this.transform_error(e);
			} catch (e) {
				Ye(e, this.#i && this.#i.parent);
				return;
			}
			typeof t == "object" && t && typeof t.then == "function" ? t.then(o, (e) => Ye(e, this.#i && this.#i.parent)) : o(t);
		});
	}
};
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/async.js
function Et(e, t, n, r) {
	let i = Ue() ? At : Mt;
	var a = e.filter((e) => !e.settled);
	if (n.length === 0 && a.length === 0) {
		r(t.map(i));
		return;
	}
	var o = W, s = Dt(), c = a.length === 1 ? a[0].promise : a.length > 1 ? Promise.all(a.map((e) => e.promise)) : null;
	function l(e) {
		s();
		try {
			r(e);
		} catch (e) {
			o.f & 16384 || Ye(e, o);
		}
		Ot();
	}
	if (n.length === 0) {
		c.then(() => l(t.map(i)));
		return;
	}
	var u = kt();
	function d() {
		Promise.all(n.map((e) => /* @__PURE__ */ jt(e))).then((e) => l([...t.map(i), ...e])).catch((e) => Ye(e, o)).finally(() => u());
	}
	c ? c.then(() => {
		s(), d(), Ot();
	}) : d();
}
function Dt() {
	var e = W, t = V, n = A, r = M;
	return function(i = !0) {
		zn(e), U(t), Be(n), i && !(e.f & 16384) && (r?.activate(), r?.apply());
	};
}
function Ot(e = !0) {
	zn(null), U(null), Be(null), e && M?.deactivate();
}
function kt() {
	var e = W, t = e.b, n = M, r = t.is_rendered();
	return t.update_pending_count(1, n), n.increment(r, e), (i = !1) => {
		t.update_pending_count(-1, n), n.decrement(r, e, i);
	};
}
/* @__NO_SIDE_EFFECTS__ */
function At(e) {
	var t = 2 | C;
	return W !== null && (W.f |= ae), {
		ctx: A,
		deps: null,
		effects: null,
		equals: Le,
		f: t,
		fn: e,
		reactions: null,
		rv: 0,
		v: i,
		wv: 0,
		parent: W,
		ac: null
	};
}
/* @__NO_SIDE_EFFECTS__ */
function jt(e, t, n) {
	let r = W;
	r === null && _e();
	var a = void 0, o = Vt(i), s = !V, c = /* @__PURE__ */ new Map();
	return xn(() => {
		var t = W, n = x();
		a = n.promise;
		try {
			Promise.resolve(e()).then(n.resolve, n.reject).finally(Ot);
		} catch (e) {
			n.reject(e), Ot();
		}
		var i = M;
		if (s) {
			if (t.f & 32768) var l = kt();
			if (r.b.is_rendered()) c.get(i)?.reject(T), c.delete(i);
			else {
				for (let e of c.values()) e.reject(T);
				c.clear();
			}
			c.set(i, n);
		}
		let u = (e, n = void 0) => {
			if (l && l(n === T), !(n === T || t.f & 16384)) {
				if (i.activate(), n) o.f |= de, Ut(o, n);
				else {
					o.f & 8388608 && (o.f ^= de), Ut(o, e);
					for (let [e, t] of c) {
						if (c.delete(e), e === i) break;
						t.reject(T);
					}
				}
				i.deactivate();
			}
		};
		n.promise.then(u, (e) => u(null, e || "unknown"));
	}), hn(() => {
		for (let e of c.values()) e.reject(T);
	}), new Promise((e) => {
		function t(n) {
			function r() {
				n === a ? e(o) : t(a);
			}
			n.then(r, r);
		}
		t(a);
	});
}
/* @__NO_SIDE_EFFECTS__ */
function Mt(e) {
	let t = /* @__PURE__ */ At(e);
	return t.equals = ze, t;
}
function Nt(e) {
	var t = e.effects;
	if (t !== null) {
		e.effects = null;
		for (var n = 0; n < t.length; n += 1) B(t[n]);
	}
}
function Pt(e) {
	var t, n = W, r = e.parent;
	if (!Ln && r !== null && r.f & 24576) return ke(), e.v;
	zn(r);
	try {
		e.f &= ~ce, Nt(e), t = Yn(e);
	} finally {
		zn(n);
	}
	return t;
}
function Ft(e) {
	var t = Pt(e);
	if (!e.equals(t) && (e.wv = Kn(), (!M?.is_fork || e.deps === null) && (M === null ? e.v = t : M.capture(e, t, !0), e.deps === null))) {
		j(e, S);
		return;
	}
	Ln || (N === null ? Ze(e) : (mn() || M?.is_fork) && N.set(e, t));
}
function It(e) {
	if (e.effects !== null) for (let t of e.effects) (t.teardown || t.ac) && (t.teardown?.(), t.ac?.abort(T), t.teardown = v, t.ac = null, Zn(t, 0), En(t));
}
function Lt(e) {
	if (e.effects !== null) for (let t of e.effects) t.teardown && Qn(t);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/sources.js
var Rt = /* @__PURE__ */ new Set(), zt = /* @__PURE__ */ new Map(), Bt = !1;
function Vt(e, t) {
	return {
		f: 0,
		v: e,
		reactions: null,
		equals: Le,
		rv: 0,
		wv: 0
	};
}
/* @__NO_SIDE_EFFECTS__ */
function Ht(e, t) {
	let n = Vt(e, t);
	return Bn(n), n;
}
/* @__NO_SIDE_EFFECTS__ */
function P(e, n = !1, r = !0) {
	let i = Vt(e);
	return n || (i.equals = ze), t && r && A !== null && A.l !== null && (A.l.s ??= []).push(i), i;
}
function F(e, t, n = !1) {
	return V !== null && (!H || V.f & 131072) && Ue() && V.f & 4325394 && (G === null || !c.call(G, e)) && De(), Ut(e, n ? qt(t) : t, lt);
}
function Ut(e, t, n = null) {
	if (!e.equals(t)) {
		zt.set(e, Ln ? t : e.v);
		var r = ft.ensure();
		if (r.capture(e, t), e.f & 2) {
			let t = e;
			e.f & 2048 && Pt(t), N === null && Ze(t);
		}
		e.wv = Kn(), Kt(e, C, n), Ue() && W !== null && W.f & 1024 && !(W.f & 96) && (J === null ? Vn([e]) : J.push(e)), !r.is_fork && Rt.size > 0 && !Bt && Wt();
	}
	return t;
}
function Wt() {
	Bt = !1;
	for (let e of Rt) e.f & 1024 && j(e, w), qn(e) && Qn(e);
	Rt.clear();
}
function Gt(e) {
	F(e, e.v + 1);
}
function Kt(e, t, n) {
	var r = e.reactions;
	if (r !== null) for (var i = Ue(), a = r.length, o = 0; o < a; o++) {
		var s = r[o], c = s.f;
		if (!(!i && s === W)) {
			var l = (c & C) === 0;
			if (l && j(s, t), c & 2) {
				var u = s;
				N?.delete(u), c & 65536 || (c & 512 && (W === null || !(W.f & 2097152)) && (s.f |= ce), Kt(u, w, n));
			} else if (l) {
				var d = s;
				c & 16 && ht !== null && ht.add(d), n === null ? yt(d) : n.push(d);
			}
		}
	}
}
function qt(e) {
	if (typeof e != "object" || !e || fe in e) return e;
	let t = g(e);
	if (t !== m && t !== h) return e;
	var n = /* @__PURE__ */ new Map(), r = o(e), a = /* @__PURE__ */ Ht(0), s = null, c = Wn, l = (e) => {
		if (Wn === c) return e();
		var t = V, n = Wn;
		U(null), Gn(c);
		var r = e();
		return U(t), Gn(n), r;
	};
	return r && n.set("length", /* @__PURE__ */ Ht(e.length, s)), new Proxy(e, {
		defineProperty(e, t, r) {
			(!("value" in r) || r.configurable === !1 || r.enumerable === !1 || r.writable === !1) && Te();
			var i = n.get(t);
			return i === void 0 ? l(() => {
				var e = /* @__PURE__ */ Ht(r.value, s);
				return n.set(t, e), e;
			}) : F(i, r.value, !0), !0;
		},
		deleteProperty(e, t) {
			var r = n.get(t);
			if (r === void 0) {
				if (t in e) {
					let e = l(() => /* @__PURE__ */ Ht(i, s));
					n.set(t, e), Gt(a);
				}
			} else F(r, i), Gt(a);
			return !0;
		},
		get(t, r, a) {
			if (r === fe) return e;
			var o = n.get(r), c = r in t;
			if (o === void 0 && (!c || f(t, r)?.writable) && (o = l(() => /* @__PURE__ */ Ht(qt(c ? t[r] : i), s)), n.set(r, o)), o !== void 0) {
				var u = Y(o);
				return u === i ? void 0 : u;
			}
			return Reflect.get(t, r, a);
		},
		getOwnPropertyDescriptor(e, t) {
			var r = Reflect.getOwnPropertyDescriptor(e, t);
			if (r && "value" in r) {
				var a = n.get(t);
				a && (r.value = Y(a));
			} else if (r === void 0) {
				var o = n.get(t), s = o?.v;
				if (o !== void 0 && s !== i) return {
					enumerable: !0,
					configurable: !0,
					value: s,
					writable: !0
				};
			}
			return r;
		},
		has(e, t) {
			if (t === fe) return !0;
			var r = n.get(t), a = r !== void 0 && r.v !== i || Reflect.has(e, t);
			return (r !== void 0 || W !== null && (!a || f(e, t)?.writable)) && (r === void 0 && (r = l(() => /* @__PURE__ */ Ht(a ? qt(e[t]) : i, s)), n.set(t, r)), Y(r) === i) ? !1 : a;
		},
		set(e, t, o, c) {
			var u = n.get(t), d = t in e;
			if (r && t === "length") for (var p = o; p < u.v; p += 1) {
				var m = n.get(p + "");
				m === void 0 ? p in e && (m = l(() => /* @__PURE__ */ Ht(i, s)), n.set(p + "", m)) : F(m, i);
			}
			if (u === void 0) (!d || f(e, t)?.writable) && (u = l(() => /* @__PURE__ */ Ht(void 0, s)), F(u, qt(o)), n.set(t, u));
			else {
				d = u.v !== i;
				var h = l(() => qt(o));
				F(u, h);
			}
			var g = Reflect.getOwnPropertyDescriptor(e, t);
			if (g?.set && g.set.call(c, o), !d) {
				if (r && typeof t == "string") {
					var _ = n.get("length"), v = Number(t);
					Number.isInteger(v) && v >= _.v && F(_, v + 1);
				}
				Gt(a);
			}
			return !0;
		},
		ownKeys(e) {
			Y(a);
			var t = Reflect.ownKeys(e).filter((e) => {
				var t = n.get(e);
				return t === void 0 || t.v !== i;
			});
			for (var [r, o] of n) o.v !== i && !(r in e) && t.push(r);
			return t;
		},
		setPrototypeOf() {
			Ee();
		}
	});
}
var Jt, Yt, Xt, Zt;
function Qt() {
	if (Jt === void 0) {
		Jt = window, Yt = /Firefox/.test(navigator.userAgent);
		var e = Element.prototype, t = Node.prototype, n = Text.prototype;
		Xt = f(t, "firstChild").get, Zt = f(t, "nextSibling").get, _(e) && (e.__click = void 0, e.__className = void 0, e.__attributes = null, e.__style = void 0, e.__e = void 0), _(n) && (n.__t = void 0);
	}
}
function I(e = "") {
	return document.createTextNode(e);
}
/* @__NO_SIDE_EFFECTS__ */
function $t(e) {
	return Xt.call(e);
}
/* @__NO_SIDE_EFFECTS__ */
function en(e) {
	return Zt.call(e);
}
function L(e, t) {
	if (!E) return /* @__PURE__ */ $t(e);
	var n = /* @__PURE__ */ $t(D);
	if (n === null) n = D.appendChild(I());
	else if (t && n.nodeType !== 3) {
		var r = I();
		return n?.before(r), O(r), r;
	}
	return t && on(n), O(n), n;
}
function tn(e, t = !1) {
	if (!E) {
		var n = /* @__PURE__ */ $t(e);
		return n instanceof Comment && n.data === "" ? /* @__PURE__ */ en(n) : n;
	}
	if (t) {
		if (D?.nodeType !== 3) {
			var r = I();
			return D?.before(r), O(r), r;
		}
		on(D);
	}
	return D;
}
function R(e, t = 1, n = !1) {
	let r = E ? D : e;
	for (var i; t--;) i = r, r = /* @__PURE__ */ en(r);
	if (!E) return r;
	if (n) {
		if (r?.nodeType !== 3) {
			var a = I();
			return r === null ? i?.after(a) : r.before(a), O(a), a;
		}
		on(r);
	}
	return O(r), r;
}
function nn(e) {
	e.textContent = "";
}
function rn() {
	return !e || ht !== null ? !1 : (W.f & ne) !== 0;
}
function an(e, t, n) {
	let r = n ? { is: n } : void 0;
	return document.createElementNS(t ?? "http://www.w3.org/1999/xhtml", e, r);
}
function on(e) {
	if (e.nodeValue.length < 65536) return;
	let t = e.nextSibling;
	for (; t !== null && t.nodeType === 3;) t.remove(), e.nodeValue += t.nodeValue, t = e.nextSibling;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/misc.js
var sn = !1;
function cn() {
	sn || (sn = !0, document.addEventListener("reset", (e) => {
		Promise.resolve().then(() => {
			if (!e.defaultPrevented) for (let t of e.target.elements) t.__on_r?.();
		});
	}, { capture: !0 }));
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/bindings/shared.js
function ln(e) {
	var t = V, n = W;
	U(null), zn(null);
	try {
		return e();
	} finally {
		U(t), zn(n);
	}
}
function un(e, t, n, r = n) {
	e.addEventListener(t, () => ln(n));
	let i = e.__on_r;
	i ? e.__on_r = () => {
		i(), r(!0);
	} : e.__on_r = () => r(!0), cn();
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/effects.js
function dn(e) {
	W === null && (V === null && xe(e), be()), Ln && ye(e);
}
function fn(e, t) {
	var n = t.last;
	n === null ? t.last = t.first = e : (n.next = e, e.prev = n, t.last = e);
}
function pn(e, t) {
	var n = W;
	n !== null && n.f & 8192 && (e |= ee);
	var r = {
		ctx: A,
		deps: null,
		nodes: null,
		f: e | C | 512,
		first: null,
		fn: t,
		last: null,
		next: null,
		parent: n,
		b: n && n.b,
		prev: null,
		teardown: null,
		wv: 0,
		ac: null
	};
	M?.register_created_effect(r);
	var i = r;
	if (e & 4) ct === null ? ft.ensure().schedule(r) : ct.push(r);
	else if (t !== null) {
		try {
			Qn(r);
		} catch (e) {
			throw B(r), e;
		}
		i.deps === null && i.teardown === null && i.nodes === null && i.first === i.last && !(i.f & 524288) && (i = i.first, e & 16 && e & 65536 && i !== null && (i.f |= ie));
	}
	if (i !== null && (i.parent = n, n !== null && fn(i, n), V !== null && V.f & 2 && !(e & 64))) {
		var a = V;
		(a.effects ??= []).push(i);
	}
	return r;
}
function mn() {
	return V !== null && !H;
}
function hn(e) {
	let t = pn(8, null);
	return j(t, S), t.teardown = e, t;
}
function gn(e) {
	dn("$effect");
	var t = W.f;
	if (!V && t & 32 && !(t & 32768)) {
		var n = A;
		(n.e ??= []).push(e);
	} else return _n(e);
}
function _n(e) {
	return pn(4 | oe, e);
}
function vn(e) {
	return dn("$effect.pre"), pn(8 | oe, e);
}
function yn(e) {
	ft.ensure();
	let t = pn(64 | ae, e);
	return () => {
		B(t);
	};
}
function bn(e) {
	ft.ensure();
	let t = pn(64 | ae, e);
	return (e = {}) => new Promise((n) => {
		e.outro ? An(t, () => {
			B(t), n(void 0);
		}) : (B(t), n(void 0));
	});
}
function xn(e) {
	return pn(ue | ae, e);
}
function Sn(e, t = 0) {
	return pn(8 | t, e);
}
function Cn(e, t = [], n = [], r = []) {
	Et(r, t, n, (t) => {
		pn(8, () => e(...t.map(Y)));
	});
}
function wn(e, t = 0) {
	return pn(16 | t, e);
}
function z(e) {
	return pn(32 | ae, e);
}
function Tn(e) {
	var t = e.teardown;
	if (t !== null) {
		let e = Ln, n = V;
		Rn(!0), U(null);
		try {
			t.call(null);
		} finally {
			Rn(e), U(n);
		}
	}
}
function En(e, t = !1) {
	var n = e.first;
	for (e.first = e.last = null; n !== null;) {
		let e = n.ac;
		e !== null && ln(() => {
			e.abort(T);
		});
		var r = n.next;
		n.f & 64 ? n.parent = null : B(n, t), n = r;
	}
}
function Dn(e) {
	for (var t = e.first; t !== null;) {
		var n = t.next;
		t.f & 32 || B(t), t = n;
	}
}
function B(e, t = !0) {
	var n = !1;
	(t || e.f & 262144) && e.nodes !== null && e.nodes.end !== null && (On(e.nodes.start, e.nodes.end), n = !0), j(e, re), En(e, t && !n), Zn(e, 0);
	var r = e.nodes && e.nodes.t;
	if (r !== null) for (let e of r) e.stop();
	Tn(e), e.f ^= re, e.f |= te;
	var i = e.parent;
	i !== null && i.first !== null && kn(e), e.next = e.prev = e.teardown = e.ctx = e.deps = e.fn = e.nodes = e.ac = e.b = null;
}
function On(e, t) {
	for (; e !== null;) {
		var n = e === t ? null : /* @__PURE__ */ en(e);
		e.remove(), e = n;
	}
}
function kn(e) {
	var t = e.parent, n = e.prev, r = e.next;
	n !== null && (n.next = r), r !== null && (r.prev = n), t !== null && (t.first === e && (t.first = r), t.last === e && (t.last = n));
}
function An(e, t, n = !0) {
	var r = [];
	jn(e, r, !0);
	var i = () => {
		n && B(e), t && t();
	}, a = r.length;
	if (a > 0) {
		var o = () => --a || i();
		for (var s of r) s.out(o);
	} else i();
}
function jn(e, t, n) {
	if (!(e.f & 8192)) {
		e.f ^= ee;
		var r = e.nodes && e.nodes.t;
		if (r !== null) for (let e of r) (e.is_global || n) && t.push(e);
		for (var i = e.first; i !== null;) {
			var a = i.next;
			if (!(i.f & 64)) {
				var o = (i.f & 65536) != 0 || (i.f & 32) != 0 && (e.f & 16) != 0;
				jn(i, t, o ? n : !1);
			}
			i = a;
		}
	}
}
function Mn(e) {
	Nn(e, !0);
}
function Nn(e, t) {
	if (e.f & 8192) {
		e.f ^= ee, e.f & 1024 || (j(e, C), ft.ensure().schedule(e));
		for (var n = e.first; n !== null;) {
			var r = n.next, i = (n.f & 65536) != 0 || (n.f & 32) != 0;
			Nn(n, i ? t : !1), n = r;
		}
		var a = e.nodes && e.nodes.t;
		if (a !== null) for (let e of a) (e.is_global || t) && e.in();
	}
}
function Pn(e, t) {
	if (e.nodes) for (var n = e.nodes.start, r = e.nodes.end; n !== null;) {
		var i = n === r ? null : /* @__PURE__ */ en(n);
		t.append(n), n = i;
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/legacy.js
var Fn = null, In = !1, Ln = !1;
function Rn(e) {
	Ln = e;
}
var V = null, H = !1;
function U(e) {
	V = e;
}
var W = null;
function zn(e) {
	W = e;
}
var G = null;
function Bn(t) {
	V !== null && (!e || V.f & 2) && (G === null ? G = [t] : G.push(t));
}
var K = null, q = 0, J = null;
function Vn(e) {
	J = e;
}
var Hn = 1, Un = 0, Wn = Un;
function Gn(e) {
	Wn = e;
}
function Kn() {
	return ++Hn;
}
function qn(e) {
	var t = e.f;
	if (t & 2048) return !0;
	if (t & 2 && (e.f &= ~ce), t & 4096) {
		for (var n = e.deps, r = n.length, i = 0; i < r; i++) {
			var a = n[i];
			if (qn(a) && Ft(a), a.wv > e.wv) return !0;
		}
		t & 512 && N === null && j(e, S);
	}
	return !1;
}
function Jn(t, n, r = !0) {
	var i = t.reactions;
	if (i !== null && !(!e && G !== null && c.call(G, t))) for (var a = 0; a < i.length; a++) {
		var o = i[a];
		o.f & 2 ? Jn(o, n, !1) : n === o && (r ? j(o, C) : o.f & 1024 && j(o, w), yt(o));
	}
}
function Yn(e) {
	var t = K, n = q, r = J, i = V, a = G, o = A, s = H, c = Wn, l = e.f;
	K = null, q = 0, J = null, V = l & 96 ? null : e, G = null, Be(e.ctx), H = !1, Wn = ++Un, e.ac !== null && (ln(() => {
		e.ac.abort(T);
	}), e.ac = null);
	try {
		e.f |= le;
		var u = e.fn, d = u();
		e.f |= ne;
		var f = e.deps, p = M?.is_fork;
		if (K !== null) {
			var m;
			if (p || Zn(e, q), f !== null && q > 0) for (f.length = q + K.length, m = 0; m < K.length; m++) f[q + m] = K[m];
			else e.deps = f = K;
			if (mn() && e.f & 512) for (m = q; m < f.length; m++) (f[m].reactions ??= []).push(e);
		} else !p && f !== null && q < f.length && (Zn(e, q), f.length = q);
		if (Ue() && J !== null && !H && f !== null && !(e.f & 6146)) for (m = 0; m < J.length; m++) Jn(J[m], e);
		if (i !== null && i !== e) {
			if (Un++, i.deps !== null) for (let e = 0; e < n; e += 1) i.deps[e].rv = Un;
			if (t !== null) for (let e of t) e.rv = Un;
			J !== null && (r === null ? r = J : r.push(...J));
		}
		return e.f & 8388608 && (e.f ^= de), d;
	} catch (e) {
		return Je(e);
	} finally {
		e.f ^= le, K = t, q = n, J = r, V = i, G = a, Be(o), H = s, Wn = c;
	}
}
function Xn(e, t) {
	let n = t.reactions;
	if (n !== null) {
		var r = s.call(n, e);
		if (r !== -1) {
			var a = n.length - 1;
			a === 0 ? n = t.reactions = null : (n[r] = n[a], n.pop());
		}
	}
	if (n === null && t.f & 2 && (K === null || !c.call(K, t))) {
		var o = t;
		o.f & 512 && (o.f ^= 512, o.f &= ~ce), o.v !== i && Ze(o), It(o), Zn(o, 0);
	}
}
function Zn(e, t) {
	var n = e.deps;
	if (n !== null) for (var r = t; r < n.length; r++) Xn(e, n[r]);
}
function Qn(e) {
	var t = e.f;
	if (!(t & 16384)) {
		j(e, S);
		var n = W, r = In;
		W = e, In = !0;
		try {
			t & 16777232 ? Dn(e) : En(e), Tn(e);
			var i = Yn(e);
			e.teardown = typeof i == "function" ? i : null, e.wv = Hn;
		} finally {
			In = r, W = n;
		}
	}
}
async function $n() {
	if (e) return new Promise((e) => {
		requestAnimationFrame(() => e()), setTimeout(() => e());
	});
	await Promise.resolve(), pt();
}
function Y(e) {
	var t = (e.f & 2) != 0;
	if (Fn?.add(e), V !== null && !H && !(W !== null && W.f & 16384) && (G === null || !c.call(G, e))) {
		var n = V.deps;
		if (V.f & 2097152) e.rv < Un && (e.rv = Un, K === null && n !== null && n[q] === e ? q++ : K === null ? K = [e] : K.push(e));
		else {
			(V.deps ??= []).push(e);
			var r = e.reactions;
			r === null ? e.reactions = [V] : c.call(r, V) || r.push(V);
		}
	}
	if (Ln && zt.has(e)) return zt.get(e);
	if (t) {
		var i = e;
		if (Ln) {
			var a = i.v;
			return (!(i.f & 1024) && i.reactions !== null || tr(i)) && (a = Pt(i)), zt.set(i, a), a;
		}
		var o = (i.f & 512) == 0 && !H && V !== null && (In || (V.f & 512) != 0), s = (i.f & ne) === 0;
		qn(i) && (o && (i.f |= 512), Ft(i)), o && !s && (Lt(i), er(i));
	}
	if (N?.has(e)) return N.get(e);
	if (e.f & 8388608) throw e.v;
	return e.v;
}
function er(e) {
	if (e.f |= 512, e.deps !== null) for (let t of e.deps) (t.reactions ??= []).push(e), t.f & 2 && !(t.f & 512) && (Lt(t), er(t));
}
function tr(e) {
	if (e.v === i) return !0;
	if (e.deps === null) return !1;
	for (let t of e.deps) if (zt.has(t) || t.f & 2 && tr(t)) return !0;
	return !1;
}
function X(e) {
	var t = H;
	try {
		return H = !0, e();
	} finally {
		H = t;
	}
}
function nr(e) {
	if (!(typeof e != "object" || !e || e instanceof EventTarget)) {
		if (fe in e) rr(e);
		else if (!Array.isArray(e)) for (let t in e) {
			let n = e[t];
			typeof n == "object" && n && fe in n && rr(n);
		}
	}
}
function rr(e, t = /* @__PURE__ */ new Set()) {
	if (typeof e == "object" && e && !(e instanceof EventTarget) && !t.has(e)) {
		t.add(e), e instanceof Date && e.getTime();
		for (let n in e) try {
			rr(e[n], t);
		} catch {}
		let n = g(e);
		if (n !== Object.prototype && n !== Array.prototype && n !== Map.prototype && n !== Set.prototype && n !== Date.prototype) {
			let t = p(n);
			for (let n in t) {
				let r = t[n].get;
				if (r) try {
					r.call(e);
				} catch {}
			}
		}
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/events.js
var ir = Symbol("events"), ar = /* @__PURE__ */ new Set(), or = /* @__PURE__ */ new Set();
function sr(e, t, n, r = {}) {
	function i(e) {
		if (r.capture || lr.call(t, e), !e.cancelBubble) return ln(() => n?.call(this, e));
	}
	return e.startsWith("pointer") || e.startsWith("touch") || e === "wheel" ? Ke(() => {
		t.addEventListener(e, i, r);
	}) : t.addEventListener(e, i, r), i;
}
function Z(e, t, n, r, i) {
	var a = {
		capture: r,
		passive: i
	}, o = sr(e, t, n, a);
	(t === document.body || t === window || t === document || t instanceof HTMLMediaElement) && hn(() => {
		t.removeEventListener(e, o, a);
	});
}
var cr = null;
function lr(e) {
	var t = this, n = t.ownerDocument, r = e.type, i = e.composedPath?.() || [], a = i[0] || e.target;
	cr = e;
	var o = 0, s = cr === e && e[ir];
	if (s) {
		var c = i.indexOf(s);
		if (c !== -1 && (t === document || t === window)) {
			e[ir] = t;
			return;
		}
		var l = i.indexOf(t);
		if (l === -1) return;
		c <= l && (o = c);
	}
	if (a = i[o] || e.target, a !== t) {
		d(e, "currentTarget", {
			configurable: !0,
			get() {
				return a || n;
			}
		});
		var u = V, f = W;
		U(null), zn(null);
		try {
			for (var p, m = []; a !== null;) {
				var h = a.assignedSlot || a.parentNode || a.host || null;
				try {
					var g = a[ir]?.[r];
					g != null && (!a.disabled || e.target === a) && g.call(a, e);
				} catch (e) {
					p ? m.push(e) : p = e;
				}
				if (e.cancelBubble || h === t || h === null) break;
				a = h;
			}
			if (p) {
				for (let e of m) queueMicrotask(() => {
					throw e;
				});
				throw p;
			}
		} finally {
			e[ir] = t, delete e.currentTarget, U(u), zn(f);
		}
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/reconciler.js
var ur = globalThis?.window?.trustedTypes && /* @__PURE__ */ globalThis.window.trustedTypes.createPolicy("svelte-trusted-html", { createHTML: (e) => e });
function dr(e) {
	return ur?.createHTML(e) ?? e;
}
function fr(e) {
	var t = an("template");
	return t.innerHTML = dr(e.replaceAll("<!>", "<!---->")), t.content;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/template.js
function pr(e, t) {
	var n = W;
	n.nodes === null && (n.nodes = {
		start: e,
		end: t,
		a: null,
		t: null
	});
}
/* @__NO_SIDE_EFFECTS__ */
function Q(e, t) {
	var n = (t & 1) != 0, r = (t & 2) != 0, i, a = !e.startsWith("<!>");
	return () => {
		if (E) return pr(D, null), D;
		i === void 0 && (i = fr(a ? e : "<!>" + e), n || (i = /* @__PURE__ */ $t(i)));
		var t = r || Yt ? document.importNode(i, !0) : i.cloneNode(!0);
		if (n) {
			var o = /* @__PURE__ */ $t(t), s = t.lastChild;
			pr(o, s);
		} else pr(t, t);
		return t;
	};
}
function $(e, t) {
	if (E) {
		var n = W;
		(!(n.f & 32768) || n.nodes.end === null) && (n.nodes.end = D), Ne();
		return;
	}
	e !== null && e.before(t);
}
[.../* @__PURE__ */ "allowfullscreen.async.autofocus.autoplay.checked.controls.default.disabled.formnovalidate.indeterminate.inert.ismap.loop.multiple.muted.nomodule.novalidate.open.playsinline.readonly.required.reversed.seamless.selected.webkitdirectory.defer.disablepictureinpicture.disableremoteplayback".split(".")];
var mr = ["touchstart", "touchmove"];
function hr(e) {
	return mr.includes(e);
}
function gr(e, t) {
	var n = t == null ? "" : typeof t == "object" ? `${t}` : t;
	n !== (e.__t ??= e.nodeValue) && (e.__t = n, e.nodeValue = `${n}`);
}
function _r(e, t) {
	return br(e, t);
}
function vr(e, t) {
	Qt(), t.intro = t.intro ?? !1;
	let n = t.target, i = E, a = D;
	try {
		for (var o = /* @__PURE__ */ $t(n); o && (o.nodeType !== 8 || o.data !== "[");) o = /* @__PURE__ */ en(o);
		if (!o) throw r;
		Me(!0), O(o);
		let i = br(e, {
			...t,
			anchor: o
		});
		return Me(!1), i;
	} catch (i) {
		if (i instanceof Error && i.message.split("\n").some((e) => e.startsWith("https://svelte.dev/e/"))) throw i;
		return i !== r && console.warn("Failed to hydrate: ", i), t.recover === !1 && Ce(), Qt(), nn(n), Me(!1), _r(e, t);
	} finally {
		Me(i), O(a);
	}
}
var yr = /* @__PURE__ */ new Map();
function br(e, { target: t, anchor: n, props: i = {}, events: a, context: o, intro: s = !0, transformError: c }) {
	Qt();
	var u = void 0, d = bn(() => {
		var s = n ?? t.appendChild(I());
		wt(s, { pending: () => {} }, (t) => {
			Ve({});
			var n = A;
			if (o && (n.c = o), a && (i.$$events = a), E && pr(t, null), u = e(t, i) || {}, E && (W.nodes.end = D, D === null || D.nodeType !== 8 || D.data !== "]")) throw Ae(), r;
			He();
		}, c);
		var d = /* @__PURE__ */ new Set(), f = (e) => {
			for (var n = 0; n < e.length; n++) {
				var r = e[n];
				if (!d.has(r)) {
					d.add(r);
					var i = hr(r);
					for (let e of [t, document]) {
						var a = yr.get(e);
						a === void 0 && (a = /* @__PURE__ */ new Map(), yr.set(e, a));
						var o = a.get(r);
						o === void 0 ? (e.addEventListener(r, lr, { passive: i }), a.set(r, 1)) : a.set(r, o + 1);
					}
				}
			}
		};
		return f(l(ar)), or.add(f), () => {
			for (var e of d) for (let n of [t, document]) {
				var r = yr.get(n), i = r.get(e);
				--i == 0 ? (n.removeEventListener(e, lr), r.delete(e), r.size === 0 && yr.delete(n)) : r.set(e, i);
			}
			or.delete(f), s !== n && s.parentNode?.removeChild(s);
		};
	});
	return xr.set(u, d), u;
}
var xr = /* @__PURE__ */ new WeakMap();
function Sr(e, t) {
	let n = xr.get(e);
	return n ? (xr.delete(e), n(t)) : Promise.resolve();
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/branches.js
var Cr = class {
	anchor;
	#e = /* @__PURE__ */ new Map();
	#t = /* @__PURE__ */ new Map();
	#n = /* @__PURE__ */ new Map();
	#r = /* @__PURE__ */ new Set();
	#i = !0;
	constructor(e, t = !0) {
		this.anchor = e, this.#i = t;
	}
	#a = (e) => {
		if (this.#e.has(e)) {
			var t = this.#e.get(e), n = this.#t.get(t);
			if (n) Mn(n), this.#r.delete(t);
			else {
				var r = this.#n.get(t);
				r && (this.#t.set(t, r.effect), this.#n.delete(t), r.fragment.lastChild.remove(), this.anchor.before(r.fragment), n = r.effect);
			}
			for (let [t, n] of this.#e) {
				if (this.#e.delete(t), t === e) break;
				let r = this.#n.get(n);
				r && (B(r.effect), this.#n.delete(n));
			}
			for (let [e, r] of this.#t) {
				if (e === t || this.#r.has(e)) continue;
				let i = () => {
					if (Array.from(this.#e.values()).includes(e)) {
						var t = document.createDocumentFragment();
						Pn(r, t), t.append(I()), this.#n.set(e, {
							effect: r,
							fragment: t
						});
					} else B(r);
					this.#r.delete(e), this.#t.delete(e);
				};
				this.#i || !n ? (this.#r.add(e), An(r, i, !1)) : i();
			}
		}
	};
	#o = (e) => {
		this.#e.delete(e);
		let t = Array.from(this.#e.values());
		for (let [e, n] of this.#n) t.includes(e) || (B(n.effect), this.#n.delete(e));
	};
	ensure(e, t) {
		var n = M, r = rn();
		if (t && !this.#t.has(e) && !this.#n.has(e)) if (r) {
			var i = document.createDocumentFragment(), a = I();
			i.append(a), this.#n.set(e, {
				effect: z(() => t(a)),
				fragment: i
			});
		} else this.#t.set(e, z(() => t(this.anchor)));
		if (this.#e.set(n, e), r) {
			for (let [t, r] of this.#t) t === e ? n.unskip_effect(r) : n.skip_effect(r);
			for (let [t, r] of this.#n) t === e ? n.unskip_effect(r.effect) : n.skip_effect(r.effect);
			n.oncommit(this.#a), n.ondiscard(this.#o);
		} else E && (this.anchor = D), this.#a(n);
	}
};
function wr(e) {
	A === null && ge("onMount"), t && A.l !== null ? Tr(A).m.push(e) : gn(() => {
		let t = X(e);
		if (typeof t == "function") return t;
	});
}
function Tr(e) {
	var t = e.l;
	return t.u ??= {
		a: [],
		b: [],
		m: []
	};
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/if.js
function Er(e, t, n = !1) {
	var r;
	E && (r = D, Ne());
	var i = new Cr(e), a = n ? ie : 0;
	function o(e, t) {
		if (E) {
			var n = Ie(r);
			if (e !== parseInt(n.substring(1))) {
				var a = Fe();
				O(a), i.anchor = a, Me(!1), i.ensure(e, t), Me(!0);
				return;
			}
		}
		i.ensure(e, t);
	}
	wn(() => {
		var e = !1;
		t((t, n = 0) => {
			e = !0, o(n, t);
		}), e || o(-1, null);
	}, a);
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/each.js
function Dr(e, t) {
	return t;
}
function Or(e, t, n) {
	for (var r = [], i = t.length, a, o = t.length, s = 0; s < i; s++) {
		let n = t[s];
		An(n, () => {
			if (a) {
				if (a.pending.delete(n), a.done.add(n), a.pending.size === 0) {
					var t = e.outrogroups;
					kr(e, l(a.done)), t.delete(a), t.size === 0 && (e.outrogroups = null);
				}
			} else --o;
		}, !1);
	}
	if (o === 0) {
		var c = r.length === 0 && n !== null;
		if (c) {
			var u = n, d = u.parentNode;
			nn(d), d.append(u), e.items.clear();
		}
		kr(e, t, !c);
	} else a = {
		pending: new Set(t),
		done: /* @__PURE__ */ new Set()
	}, (e.outrogroups ??= /* @__PURE__ */ new Set()).add(a);
}
function kr(e, t, n = !0) {
	var r;
	if (e.pending.size > 0) {
		r = /* @__PURE__ */ new Set();
		for (let t of e.pending.values()) for (let n of t) r.add(e.items.get(n).e);
	}
	for (var i = 0; i < t.length; i++) {
		var a = t[i];
		r?.has(a) ? (a.f |= se, Pn(a, document.createDocumentFragment())) : B(t[i], n);
	}
}
var Ar;
function jr(e, t, n, r, i, a = null) {
	var s = e, c = /* @__PURE__ */ new Map();
	if (t & 4) {
		var u = e;
		s = E ? O(/* @__PURE__ */ $t(u)) : u.appendChild(I());
	}
	E && Ne();
	var d = null, f = /* @__PURE__ */ Mt(() => {
		var e = n();
		return o(e) ? e : e == null ? [] : l(e);
	}), p, m = /* @__PURE__ */ new Map(), h = !0;
	function g(e) {
		v.effect.f & 16384 || (v.pending.delete(e), v.fallback = d, Nr(v, p, s, t, r), d !== null && (p.length === 0 ? d.f & 33554432 ? (d.f ^= se, Fr(d, null, s)) : Mn(d) : An(d, () => {
			d = null;
		})));
	}
	function _(e) {
		v.pending.delete(e);
	}
	var v = {
		effect: wn(() => {
			p = Y(f);
			var e = p.length;
			let o = !1;
			E && Ie(s) === "[!" != (e === 0) && (s = Fe(), O(s), Me(!1), o = !0);
			for (var l = /* @__PURE__ */ new Set(), u = M, v = rn(), y = 0; y < e; y += 1) {
				E && D.nodeType === 8 && D.data === "]" && (s = D, o = !0, Me(!1));
				var b = p[y], x = r(b, y), S = h ? null : c.get(x);
				S ? (S.v && Ut(S.v, b), S.i && Ut(S.i, y), v && u.unskip_effect(S.e)) : (S = Pr(c, h ? s : Ar ??= I(), b, x, y, i, t, n), h || (S.e.f |= se), c.set(x, S)), l.add(x);
			}
			if (e === 0 && a && !d && (h ? d = z(() => a(s)) : (d = z(() => a(Ar ??= I())), d.f |= se)), e > l.size && ve("", "", ""), E && e > 0 && O(Fe()), !h) if (m.set(u, l), v) {
				for (let [e, t] of c) l.has(e) || u.skip_effect(t.e);
				u.oncommit(g), u.ondiscard(_);
			} else g(u);
			o && Me(!0), Y(f);
		}),
		flags: t,
		items: c,
		pending: m,
		outrogroups: null,
		fallback: d
	};
	h = !1, E && (s = D);
}
function Mr(e) {
	for (; e !== null && !(e.f & 32);) e = e.next;
	return e;
}
function Nr(e, t, n, r, i) {
	var a = (r & 8) != 0, o = t.length, s = e.items, c = Mr(e.effect.first), u, d = null, f, p = [], m = [], h, g, _, v;
	if (a) for (v = 0; v < o; v += 1) h = t[v], g = i(h, v), _ = s.get(g).e, _.f & 33554432 || (_.nodes?.a?.measure(), (f ??= /* @__PURE__ */ new Set()).add(_));
	for (v = 0; v < o; v += 1) {
		if (h = t[v], g = i(h, v), _ = s.get(g).e, e.outrogroups !== null) for (let t of e.outrogroups) t.pending.delete(_), t.done.delete(_);
		if (_.f & 8192 && (Mn(_), a && (_.nodes?.a?.unfix(), (f ??= /* @__PURE__ */ new Set()).delete(_))), _.f & 33554432) if (_.f ^= se, _ === c) Fr(_, null, n);
		else {
			var y = d ? d.next : c;
			_ === e.effect.last && (e.effect.last = _.prev), _.prev && (_.prev.next = _.next), _.next && (_.next.prev = _.prev), Ir(e, d, _), Ir(e, _, y), Fr(_, y, n), d = _, p = [], m = [], c = Mr(d.next);
			continue;
		}
		if (_ !== c) {
			if (u !== void 0 && u.has(_)) {
				if (p.length < m.length) {
					var b = m[0], x;
					d = b.prev;
					var S = p[0], C = p[p.length - 1];
					for (x = 0; x < p.length; x += 1) Fr(p[x], b, n);
					for (x = 0; x < m.length; x += 1) u.delete(m[x]);
					Ir(e, S.prev, C.next), Ir(e, d, S), Ir(e, C, b), c = b, d = C, --v, p = [], m = [];
				} else u.delete(_), Fr(_, c, n), Ir(e, _.prev, _.next), Ir(e, _, d === null ? e.effect.first : d.next), Ir(e, d, _), d = _;
				continue;
			}
			for (p = [], m = []; c !== null && c !== _;) (u ??= /* @__PURE__ */ new Set()).add(c), m.push(c), c = Mr(c.next);
			if (c === null) continue;
		}
		_.f & 33554432 || p.push(_), d = _, c = Mr(_.next);
	}
	if (e.outrogroups !== null) {
		for (let t of e.outrogroups) t.pending.size === 0 && (kr(e, l(t.done)), e.outrogroups?.delete(t));
		e.outrogroups.size === 0 && (e.outrogroups = null);
	}
	if (c !== null || u !== void 0) {
		var w = [];
		if (u !== void 0) for (_ of u) _.f & 8192 || w.push(_);
		for (; c !== null;) !(c.f & 8192) && c !== e.fallback && w.push(c), c = Mr(c.next);
		var ee = w.length;
		if (ee > 0) {
			var te = r & 4 && o === 0 ? n : null;
			if (a) {
				for (v = 0; v < ee; v += 1) w[v].nodes?.a?.measure();
				for (v = 0; v < ee; v += 1) w[v].nodes?.a?.fix();
			}
			Or(e, w, te);
		}
	}
	a && Ke(() => {
		if (f !== void 0) for (_ of f) _.nodes?.a?.apply();
	});
}
function Pr(e, t, n, r, i, a, o, s) {
	var c = o & 1 ? o & 16 ? Vt(n) : /* @__PURE__ */ P(n, !1, !1) : null, l = o & 2 ? Vt(i) : null;
	return {
		v: c,
		i: l,
		e: z(() => (a(t, c ?? n, l ?? i, s), () => {
			e.delete(r);
		}))
	};
}
function Fr(e, t, n) {
	if (e.nodes) for (var r = e.nodes.start, i = e.nodes.end, a = t && !(t.f & 33554432) ? t.nodes.start : n; r !== null;) {
		var o = /* @__PURE__ */ en(r);
		if (a.before(r), r === i) return;
		r = o;
	}
}
function Ir(e, t, n) {
	t === null ? e.effect.first = n : t.next = n, n === null ? e.effect.last = t : n.prev = t;
}
//#endregion
//#region node_modules/svelte/src/internal/shared/attributes.js
var Lr = [..." 	\n\r\f\xA0\v﻿"];
function Rr(e, t, n) {
	var r = e == null ? "" : "" + e;
	if (t && (r = r ? r + " " + t : t), n) {
		for (var i of Object.keys(n)) if (n[i]) r = r ? r + " " + i : i;
		else if (r.length) for (var a = i.length, o = 0; (o = r.indexOf(i, o)) >= 0;) {
			var s = o + a;
			(o === 0 || Lr.includes(r[o - 1])) && (s === r.length || Lr.includes(r[s])) ? r = (o === 0 ? "" : r.substring(0, o)) + r.substring(s + 1) : o = s;
		}
	}
	return r === "" ? null : r;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/class.js
function zr(e, t, n, r, i, a) {
	var o = e.__className;
	if (E || o !== n || o === void 0) {
		var s = Rr(n, r, a);
		(!E || s !== e.getAttribute("class")) && (s == null ? e.removeAttribute("class") : t ? e.className = s : e.setAttribute("class", s)), e.__className = n;
	} else if (a && i !== a) for (var c in a) {
		var l = !!a[c];
		(i == null || l !== !!i[c]) && e.classList.toggle(c, l);
	}
	return a;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/attributes.js
var Br = Symbol("is custom element"), Vr = Symbol("is html"), Hr = he ? "link" : "LINK", Ur = he ? "progress" : "PROGRESS";
function Wr(e) {
	if (E) {
		var t = !1, n = () => {
			if (!t) {
				if (t = !0, e.hasAttribute("value")) {
					var n = e.value;
					Kr(e, "value", null), e.value = n;
				}
				if (e.hasAttribute("checked")) {
					var r = e.checked;
					Kr(e, "checked", null), e.checked = r;
				}
			}
		};
		e.__on_r = n, Ke(n), cn();
	}
}
function Gr(e, t) {
	var n = qr(e);
	n.value === (n.value = t ?? void 0) || e.value === t && (t !== 0 || e.nodeName !== Ur) || (e.value = t ?? "");
}
function Kr(e, t, n, r) {
	var i = qr(e);
	E && (i[t] = e.getAttribute(t), t === "src" || t === "srcset" || t === "href" && e.nodeName === Hr) || i[t] !== (i[t] = n) && (t === "loading" && (e[me] = n), n == null ? e.removeAttribute(t) : typeof n != "string" && Yr(e).includes(t) ? e[t] = n : e.setAttribute(t, n));
}
function qr(e) {
	return e.__attributes ??= {
		[Br]: e.nodeName.includes("-"),
		[Vr]: e.namespaceURI === a
	};
}
var Jr = /* @__PURE__ */ new Map();
function Yr(e) {
	var t = e.getAttribute("is") || e.nodeName, n = Jr.get(t);
	if (n) return n;
	Jr.set(t, n = []);
	for (var r, i = e, a = Element.prototype; a !== i;) {
		for (var o in r = p(i), r) r[o].set && n.push(o);
		i = g(i);
	}
	return n;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/bindings/input.js
function Xr(t, n, r = n) {
	var i = /* @__PURE__ */ new WeakSet();
	un(t, "input", async (e) => {
		var a = e ? t.defaultValue : t.value;
		if (a = Zr(t) ? Qr(a) : a, r(a), M !== null && i.add(M), await $n(), a !== (a = n())) {
			var o = t.selectionStart, s = t.selectionEnd, c = t.value.length;
			if (t.value = a ?? "", s !== null) {
				var l = t.value.length;
				o === s && s === c && l > c ? (t.selectionStart = l, t.selectionEnd = l) : (t.selectionStart = o, t.selectionEnd = Math.min(s, l));
			}
		}
	}), (E && t.defaultValue !== t.value || X(n) == null && t.value) && (r(Zr(t) ? Qr(t.value) : t.value), M !== null && i.add(M)), Sn(() => {
		var r = n();
		if (t === document.activeElement) {
			var a = e ? it : M;
			if (i.has(a)) return;
		}
		Zr(t) && r === Qr(t.value) || t.type === "date" && !r && !t.value || r !== t.value && (t.value = r ?? "");
	});
}
function Zr(e) {
	var t = e.type;
	return t === "number" || t === "range";
}
function Qr(e) {
	return e === "" ? null : +e;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/legacy/event-modifiers.js
function $r(e) {
	return function(...t) {
		return t[0].stopPropagation(), e?.apply(this, t);
	};
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/legacy/lifecycle.js
function ei(e = !1) {
	let t = A, n = t.l.u;
	if (!n) return;
	let r = () => nr(t.s);
	if (e) {
		let e = 0, n = {}, i = /* @__PURE__ */ At(() => {
			let r = !1, i = t.s;
			for (let e in i) i[e] !== n[e] && (n[e] = i[e], r = !0);
			return r && e++, e;
		});
		r = () => Y(i);
	}
	n.b.length && vn(() => {
		ti(t, r), b(n.b);
	}), gn(() => {
		let e = X(() => n.m.map(y));
		return () => {
			for (let t of e) typeof t == "function" && t();
		};
	}), n.a.length && gn(() => {
		ti(t, r), b(n.a);
	});
}
function ti(e, t) {
	if (e.l.s) for (let t of e.l.s) Y(t);
	t();
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/legacy/misc.js
function ni(e, t) {
	var n = e.$$events?.[t.type];
	for (var r of o(n) ? n.slice() : n == null ? [] : [n]) r.call(this, t);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/props.js
function ri(e, n, r, i) {
	var a = !t || (r & 2) != 0, o = (r & 8) != 0, s = (r & 16) != 0, c = i, l = !0, u = () => (l && (l = !1, c = s ? X(i) : i), c);
	let d;
	if (o) {
		var p = fe in e || pe in e;
		d = f(e, n)?.set ?? (p && n in e ? (t) => e[n] = t : void 0);
	}
	var m, h = !1;
	o ? [m, h] = nt(() => e[n]) : m = e[n], m === void 0 && i !== void 0 && (m = u(), d && (a && we(n), d(m)));
	var g = a ? () => {
		var t = e[n];
		return t === void 0 ? u() : (l = !0, t);
	} : () => {
		var t = e[n];
		return t !== void 0 && (c = void 0), t === void 0 ? c : t;
	};
	if (a && !(r & 4)) return g;
	if (d) {
		var _ = e.$$legacy;
		return (function(e, t) {
			return arguments.length > 0 ? ((!a || !t || _ || h) && d(t ? g() : e), e) : g();
		});
	}
	var v = !1, y = (r & 1 ? At : Mt)(() => (v = !1, g()));
	o && Y(y);
	var b = W;
	return (function(e, t) {
		if (arguments.length > 0) {
			let n = t ? Y(y) : a && o ? qt(e) : e;
			return F(y, n), v = !0, c !== void 0 && (c = n), e;
		}
		return Ln && v || b.f & 16384 ? y.v : Y(y);
	});
}
//#endregion
//#region node_modules/svelte/src/legacy/legacy-client.js
function ii(e) {
	return new ai(e);
}
var ai = class {
	#e;
	#t;
	constructor(t) {
		var n = /* @__PURE__ */ new Map(), r = (e, t) => {
			var r = /* @__PURE__ */ P(t, !1, !1);
			return n.set(e, r), r;
		};
		let i = new Proxy({
			...t.props || {},
			$$events: {}
		}, {
			get(e, t) {
				return Y(n.get(t) ?? r(t, Reflect.get(e, t)));
			},
			has(e, t) {
				return t === pe ? !0 : (Y(n.get(t) ?? r(t, Reflect.get(e, t))), Reflect.has(e, t));
			},
			set(e, t, i) {
				return F(n.get(t) ?? r(t, i), i), Reflect.set(e, t, i);
			}
		});
		this.#t = (t.hydrate ? vr : _r)(t.component, {
			target: t.target,
			anchor: t.anchor,
			props: i,
			context: t.context,
			intro: t.intro ?? !1,
			recover: t.recover,
			transformError: t.transformError
		}), !e && (!t?.props?.$$host || t.sync === !1) && pt(), this.#e = i.$$events;
		for (let e of Object.keys(this.#t)) e === "$set" || e === "$destroy" || e === "$on" || d(this, e, {
			get() {
				return this.#t[e];
			},
			set(t) {
				this.#t[e] = t;
			},
			enumerable: !0
		});
		this.#t.$set = (e) => {
			Object.assign(i, e);
		}, this.#t.$destroy = () => {
			Sr(this.#t);
		};
	}
	$set(e) {
		this.#t.$set(e);
	}
	$on(e, t) {
		this.#e[e] = this.#e[e] || [];
		let n = (...e) => t.call(this, ...e);
		return this.#e[e].push(n), () => {
			this.#e[e] = this.#e[e].filter((e) => e !== n);
		};
	}
	$destroy() {
		this.#t.$destroy();
	}
}, oi;
typeof HTMLElement == "function" && (oi = class extends HTMLElement {
	$$ctor;
	$$s;
	$$c;
	$$cn = !1;
	$$d = {};
	$$r = !1;
	$$p_d = {};
	$$l = {};
	$$l_u = /* @__PURE__ */ new Map();
	$$me;
	$$shadowRoot = null;
	constructor(e, t, n) {
		super(), this.$$ctor = e, this.$$s = t, n && (this.$$shadowRoot = this.attachShadow(n));
	}
	addEventListener(e, t, n) {
		if (this.$$l[e] = this.$$l[e] || [], this.$$l[e].push(t), this.$$c) {
			let n = this.$$c.$on(e, t);
			this.$$l_u.set(t, n);
		}
		super.addEventListener(e, t, n);
	}
	removeEventListener(e, t, n) {
		if (super.removeEventListener(e, t, n), this.$$c) {
			let e = this.$$l_u.get(t);
			e && (e(), this.$$l_u.delete(t));
		}
	}
	async connectedCallback() {
		if (this.$$cn = !0, !this.$$c) {
			if (await Promise.resolve(), !this.$$cn || this.$$c) return;
			function e(e) {
				return (t) => {
					let n = an("slot");
					e !== "default" && (n.name = e), $(t, n);
				};
			}
			let t = {}, n = ci(this);
			for (let r of this.$$s) r in n && (r === "default" && !this.$$d.children ? (this.$$d.children = e(r), t.default = !0) : t[r] = e(r));
			for (let e of this.attributes) {
				let t = this.$$g_p(e.name);
				t in this.$$d || (this.$$d[t] = si(t, e.value, this.$$p_d, "toProp"));
			}
			for (let e in this.$$p_d) !(e in this.$$d) && this[e] !== void 0 && (this.$$d[e] = this[e], delete this[e]);
			this.$$c = ii({
				component: this.$$ctor,
				target: this.$$shadowRoot || this,
				props: {
					...this.$$d,
					$$slots: t,
					$$host: this
				}
			}), this.$$me = yn(() => {
				Sn(() => {
					this.$$r = !0;
					for (let e of u(this.$$c)) {
						if (!this.$$p_d[e]?.reflect) continue;
						this.$$d[e] = this.$$c[e];
						let t = si(e, this.$$d[e], this.$$p_d, "toAttribute");
						t == null ? this.removeAttribute(this.$$p_d[e].attribute || e) : this.setAttribute(this.$$p_d[e].attribute || e, t);
					}
					this.$$r = !1;
				});
			});
			for (let e in this.$$l) for (let t of this.$$l[e]) {
				let n = this.$$c.$on(e, t);
				this.$$l_u.set(t, n);
			}
			this.$$l = {};
		}
	}
	attributeChangedCallback(e, t, n) {
		this.$$r || (e = this.$$g_p(e), this.$$d[e] = si(e, n, this.$$p_d, "toProp"), this.$$c?.$set({ [e]: this.$$d[e] }));
	}
	disconnectedCallback() {
		this.$$cn = !1, Promise.resolve().then(() => {
			!this.$$cn && this.$$c && (this.$$c.$destroy(), this.$$me(), this.$$c = void 0);
		});
	}
	$$g_p(e) {
		return u(this.$$p_d).find((t) => this.$$p_d[t].attribute === e || !this.$$p_d[t].attribute && t.toLowerCase() === e) || e;
	}
});
function si(e, t, n, r) {
	let i = n[e]?.type;
	if (t = i === "Boolean" && typeof t != "boolean" ? t != null : t, !r || !n[e]) return t;
	if (r === "toAttribute") switch (i) {
		case "Object":
		case "Array": return t == null ? null : JSON.stringify(t);
		case "Boolean": return t ? "" : null;
		case "Number": return t ?? null;
		default: return t;
	}
	else switch (i) {
		case "Object":
		case "Array": return t && JSON.parse(t);
		case "Boolean": return t;
		case "Number": return t == null ? t : +t;
		default: return t;
	}
}
function ci(e) {
	let t = {};
	return e.childNodes.forEach((e) => {
		t[e.slot || "default"] = !0;
	}), t;
}
function li(e, t, n, r, i, a) {
	let o = class extends oi {
		constructor() {
			super(e, n, i), this.$$p_d = t;
		}
		static get observedAttributes() {
			return u(t).map((e) => (t[e].attribute || e).toLowerCase());
		}
	};
	return u(t).forEach((e) => {
		d(o.prototype, e, {
			get() {
				return this.$$c && e in this.$$c ? this.$$c[e] : this.$$d[e];
			},
			set(n) {
				n = si(e, n, t), this.$$d[e] = n;
				var r = this.$$c;
				r && (f(r, e)?.get ? r[e] = n : r.$set({ [e]: n }));
			}
		});
	}), r.forEach((e) => {
		d(o.prototype, e, { get() {
			return this.$$c?.[e];
		} });
	}), a && (o = a(o)), e.element = o, o;
}
//#endregion
//#region MusicBrainzCard.svelte
var ui = /* @__PURE__ */ Q("<div class=\"p-5 text-center text-[var(--text-muted)]\">Loading...</div>"), di = /* @__PURE__ */ Q("<input type=\"text\" class=\"px-3 py-2 bg-background/50 border border-border rounded-global text-sm text-[var(--text-primary)] w-full box-border opacity-70 cursor-not-allowed select-all\" readonly=\"\" disabled=\"\"/> <p class=\"text-xs text-[var(--text-muted)] mt-1\" style=\"margin-top:6px;\">Add this URI as a callback URL in your MusicBrainz application settings.</p>", 1), fi = /* @__PURE__ */ Q("<button class=\"px-4 py-2 bg-white/10 text-[var(--text-primary)] border border-white/20 rounded-global transition-colors hover:bg-white/15 disabled:opacity-50 disabled:cursor-not-allowed active:scale-95\">+ Add Account</button>"), pi = /* @__PURE__ */ Q("<span class=\"text-[12px] px-2 py-1 rounded-[4px] bg-[#00e676]/20 text-[#00e676]\">✓ Authenticated</span>"), mi = /* @__PURE__ */ Q("<span class=\"text-[12px] px-2 py-1 rounded-[4px] bg-yellow-500/20 text-yellow-500\">⚠ Not Authenticated</span>"), hi = /* @__PURE__ */ Q("<span class=\"text-[12px] px-2 py-1 rounded-[4px] bg-[var(--color-primary)]/20 text-[var(--color-primary)]\">● Active</span>"), gi = /* @__PURE__ */ Q("<div class=\"flex justify-between items-center p-3 bg-white/5 border border-white/10 rounded-global\"><div class=\"flex flex-col gap-1\"><div class=\"font-medium text-[14px]\"> </div> <div class=\"flex gap-[6px] flex-wrap\"><!> <!></div></div> <div class=\"flex gap-2 items-center flex-wrap\"><button class=\"bg-transparent text-[var(--color-primary)] px-2 py-1 hover:underline active:scale-95 transition-all duration-200\"> </button> <button> </button> <button class=\"px-4 py-2 bg-red-500/20 text-red-500 border-none rounded-global transition-colors hover:bg-red-500/30 active:scale-95\">✕</button></div></div>"), _i = /* @__PURE__ */ Q("<div class=\"p-4 text-center text-[var(--text-muted)] text-sm\">No accounts added yet. Click \"Add Account\" to get started.</div>"), vi = /* @__PURE__ */ Q("<div class=\"mb-6\"><h3 class=\"m-0 mb-4 text-base font-semibold\">Custom API Base URL</h3> <p class=\"text-xs text-[var(--text-muted)] mt-1\">Point this to a local MusicBrainz Docker container to go 100% offline.</p> <div class=\"flex flex-col gap-3\"><div class=\"flex flex-col gap-1\"><label class=\"text-[13px] font-medium text-[var(--text-primary)]\" for=\"mb-api-base-url\">API Base URL</label> <input id=\"mb-api-base-url\" type=\"text\" class=\"px-3 py-2 bg-background border border-border rounded-global text-sm text-[var(--text-primary)] w-full box-border focus:outline-none focus:border-accent\" placeholder=\"https://musicbrainz.org/ws/2\"/></div> <button class=\"px-4 py-2 bg-accent text-black font-medium rounded-global transition-colors hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed active:scale-95\">Save Settings</button></div></div> <div class=\"mb-6\"><h3 class=\"m-0 mb-4 text-base font-semibold\">Application Credentials</h3> <p class=\"text-xs text-[var(--text-muted)] mt-1\">Register an application at <a href=\"https://musicbrainz.org/account/applications\" target=\"_blank\" rel=\"noopener noreferrer\">musicbrainz.org/account/applications</a> to obtain a Client ID and Secret. These are required for OAuth logins and ISRC submissions.</p> <div class=\"flex flex-col gap-3\"><div class=\"flex flex-col gap-1\"><label class=\"text-[13px] font-medium text-[var(--text-primary)]\" for=\"mb-client-id\">Client ID</label> <input id=\"mb-client-id\" type=\"text\" class=\"px-3 py-2 bg-background border border-border rounded-global text-sm text-[var(--text-primary)] w-full box-border focus:outline-none focus:border-accent\" placeholder=\"Enter your MusicBrainz Client ID\"/></div> <div class=\"flex flex-col gap-1\"><label class=\"text-[13px] font-medium text-[var(--text-primary)]\" for=\"mb-client-secret\">Client Secret</label> <div class=\"relative flex items-center\"><input id=\"mb-client-secret\" class=\"px-3 py-2 bg-background border border-border rounded-global text-sm text-[var(--text-primary)] w-full box-border focus:outline-none focus:border-accent\"/> <button type=\"button\" class=\"absolute right-2 bg-transparent border-none cursor-pointer text-lg p-1 opacity-60 hover:opacity-100 transition-opacity active:scale-95\"> </button></div></div> <button class=\"px-4 py-2 bg-accent text-black font-medium rounded-global transition-colors hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed active:scale-95\"> </button></div></div> <div class=\"mb-6\"><div class=\"mb-3\"><h3 class=\"m-0 mb-4 text-base font-semibold\">OAuth Redirect URI (Auto-generated)</h3> <button class=\"px-4 py-2 bg-white/10 text-[var(--text-primary)] border border-white/20 rounded-global transition-colors hover:bg-white/15 disabled:opacity-50 disabled:cursor-not-allowed active:scale-95\"> </button></div> <!></div> <div class=\"mb-6\"><div class=\"mb-3\"><h3 class=\"m-0 mb-4 text-base font-semibold\"> </h3> <p class=\"text-xs text-[var(--text-muted)] mt-1\">Each account represents a MusicBrainz user that will authenticate via OAuth.\n          Authenticated accounts can contribute ISRCs and metadata to MusicBrainz.</p> <!></div> <div class=\"flex flex-col gap-2\"></div></div>", 1), yi = /* @__PURE__ */ Q("<div class=\"fixed inset-0 bg-black/60 flex items-center justify-center z-[1000]\"><div class=\"bg-[#1e1e2e] rounded-[10px] p-0 min-w-[420px] max-w-[90vw] border border-white/15\"><div class=\"flex justify-between items-center px-5 py-4 border-b border-white/10\"><h3 class=\"m-0 mb-4 text-base font-semibold\">Add MusicBrainz Account</h3> <button class=\"bg-transparent border-none text-[18px] cursor-pointer text-[var(--text-muted)] p-0 leading-none active:scale-95 transition-all duration-200\">✕</button></div> <div class=\"p-5 flex flex-col gap-[14px]\"><label class=\"flex flex-col gap-[6px]\"><span class=\"text-[13px] font-medium text-[var(--text-primary)]\">Display Name</span> <input type=\"text\" placeholder=\"e.g. My MusicBrainz Username\" class=\"px-3 py-2 bg-background border border-border rounded-global text-sm text-[var(--text-primary)] w-full box-border focus:outline-none focus:border-accent\"/></label> <p class=\"text-[12px] text-[var(--text-muted)] m-0\">Give this slot a friendly name. After adding, click \"Authenticate\" to link it\n          to a real MusicBrainz account via OAuth.</p></div> <div class=\"flex justify-end gap-[10px] px-5 py-4 border-t border-white/10\"><button class=\"px-4 py-2 bg-white/10 text-[var(--text-primary)] border border-white/20 rounded-global transition-colors hover:bg-white/15 disabled:opacity-50 disabled:cursor-not-allowed active:scale-95\">Cancel</button> <button class=\"px-4 py-2 bg-accent text-black font-medium rounded-global transition-colors hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed active:scale-95\"> </button></div></div></div>"), bi = /* @__PURE__ */ Q("<section class=\"p-6 bg-[var(--bg-surface)] backdrop-blur-md border border-[var(--border-subtle)] rounded-global mb-4\"><div class=\"flex justify-between items-center mb-5 pb-3 border-b border-[var(--border-subtle)]\"><div class=\"flex items-center gap-3\"><h2 class=\"m-0 text-xl font-semibold\">MusicBrainz</h2> <span class=\"text-[12px] px-2 py-1 rounded-[4px] bg-[var(--color-primary)]/20 text-[var(--color-primary)]\">Metadata</span></div></div> <!></section> <!>", 1);
function xi(e, t) {
	Ve(t, !1);
	let n = ri(t, "apiBase", 12, ""), r = /* @__PURE__ */ P(!0), i = /* @__PURE__ */ P([]), a = /* @__PURE__ */ P(""), o = /* @__PURE__ */ P(""), s = /* @__PURE__ */ P(""), c = !1, l = /* @__PURE__ */ P(!1), u = /* @__PURE__ */ P(!1), d = /* @__PURE__ */ P(!1), f = /* @__PURE__ */ P(!1), p = /* @__PURE__ */ P("https://musicbrainz.org/ws/2"), m = /* @__PURE__ */ P(!1), h = /* @__PURE__ */ P(""), g = /* @__PURE__ */ P(!1);
	wr(async () => {
		await _(), F(r, !1);
	});
	async function _() {
		try {
			let e = await fetch(`${n()}/musicbrainz/accounts`);
			e.data && (F(i, e.data.accounts || []), F(a, e.data.redirect_uri || ""), c = e.data.client_id_configured || !1, F(l, e.data.client_secret_configured || !1), F(f, !!Y(a)));
			let t = await fetch(`${n()}/providers/musicbrainz/settings`);
			t.data?.settings && F(p, t.data.settings.api_base_url || "https://musicbrainz.org/ws/2");
			let r = await fetch(`${n()}/providers/musicbrainz/credentials`);
			r.data?.credentials && (F(o, r.data.credentials.client_id || ""), Y(l));
		} catch (e) {
			console.error("Failed to load MusicBrainz data:", e), console.error("Failed to load MusicBrainz settings");
		}
	}
	async function v() {
		if (!Y(o).trim()) {
			console.error("Client ID is required");
			return;
		}
		let e = { client_id: Y(o) };
		if (Y(s).trim()) e.client_secret = Y(s);
		else if (!Y(l)) {
			console.error("Client Secret is required");
			return;
		}
		try {
			F(d, !0), await fetch(`${n()}/providers/musicbrainz/credentials`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ credentials: e })
			}), console.log("MusicBrainz credentials saved"), F(s, ""), await _();
		} catch (e) {
			console.error("Failed to save credentials"), console.error(e);
		} finally {
			F(d, !1);
		}
	}
	async function y() {
		try {
			await fetch(`${n()}/providers/musicbrainz/settings`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ settings: { api_base_url: Y(p) } })
			}), console.log("MusicBrainz settings saved");
		} catch (e) {
			console.error("Failed to save settings:", e);
		}
	}
	function b() {
		F(h, ""), F(m, !0);
	}
	function x() {
		F(m, !1), F(h, "");
	}
	async function S() {
		let e = Y(h).trim();
		if (!e) {
			console.error("Account name is required");
			return;
		}
		try {
			F(g, !0), await fetch(`${n()}/musicbrainz/accounts`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ account_name: e })
			}), console.log("Account added"), x(), await _();
		} catch (e) {
			console.error("Failed to add account"), console.error(e);
		} finally {
			F(g, !1);
		}
	}
	async function C(e, t) {
		if (confirm(`Delete account "${t}"? This will also remove its stored tokens.`)) try {
			await fetch(`${n()}/musicbrainz/accounts/${e}`, { method: "DELETE" }), console.log("Account deleted"), await _();
		} catch {
			console.error("Failed to delete account");
		}
	}
	async function w(e, t) {
		try {
			await fetch(`${n()}/musicbrainz/accounts/${e}/activate`, {
				method: "PUT",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ is_active: !t })
			}), console.log(t ? "Account deactivated" : "Account activated"), await _();
		} catch {
			console.error("Failed to update account status");
		}
	}
	async function ee(e) {
		if (!c || !Y(l)) {
			console.log("Save your MusicBrainz Client ID and Client Secret before authenticating.", "error");
			return;
		}
		try {
			let t = (await fetch(`${n()}/musicbrainz/auth`, { params: { account_id: e } })).data?.auth_url;
			t ? (window.open(t, "_blank", "noopener,noreferrer"), setTimeout(async () => {
				await _();
			}, 5e3)) : console.error("Failed to get MusicBrainz auth URL");
		} catch (e) {
			let t = e?.response?.data?.error || "Failed to start OAuth";
			console.error(t);
		}
	}
	var te = {
		get apiBase() {
			return n();
		},
		set apiBase(e) {
			n(e), pt();
		}
	};
	ei();
	var ne = bi(), re = tn(ne), ie = R(L(re), 2), ae = (e) => {
		$(e, ui());
	}, oe = (e) => {
		var t = vi(), n = tn(t), r = R(L(n), 4), c = L(r), m = R(L(c), 2);
		Wr(m), k(c);
		var h = R(c, 2);
		k(r), k(n);
		var g = R(n, 2), _ = R(L(g), 4), x = L(_), S = R(L(x), 2);
		Wr(S), k(x);
		var te = R(x, 2), ne = R(L(te), 2), re = L(ne);
		Wr(re);
		var ie = R(re, 2), ae = L(ie, !0);
		k(ie), k(ne), k(te);
		var oe = R(te, 2), se = L(oe, !0);
		k(oe), k(_), k(g);
		var ce = R(g, 2), le = L(ce), ue = R(L(le), 2), de = L(ue, !0);
		k(ue), k(le);
		var fe = R(le, 2), pe = (e) => {
			var t = di(), n = tn(t);
			Wr(n), Pe(2), Cn(() => Gr(n, Y(a))), $(e, t);
		};
		Er(fe, (e) => {
			Y(f) || e(pe);
		}), k(ce);
		var me = R(ce, 2), T = L(me), he = L(T), ge = L(he);
		k(he);
		var _e = R(he, 4), ve = (e) => {
			var t = fi();
			Z("click", t, b), $(e, t);
		};
		Er(_e, (e) => {
			Y(i), X(() => Y(i).length < 10) && e(ve);
		}), k(T);
		var ye = R(T, 2);
		jr(ye, 5, () => Y(i), Dr, (e, t) => {
			var n = gi(), r = L(n), i = L(r), a = L(i, !0);
			k(i);
			var o = R(i, 2), s = L(o), c = (e) => {
				$(e, pi());
			}, l = (e) => {
				$(e, mi());
			};
			Er(s, (e) => {
				Y(t), X(() => Y(t).is_authenticated) ? e(c) : e(l, -1);
			});
			var u = R(s, 2), d = (e) => {
				$(e, hi());
			};
			Er(u, (e) => {
				Y(t), X(() => Y(t).is_active) && e(d);
			}), k(o), k(r);
			var f = R(r, 2), p = L(f), m = L(p, !0);
			k(p);
			var h = R(p, 2);
			let g;
			var _ = L(h, !0);
			k(h);
			var v = R(h, 2);
			k(f), k(n), Cn(() => {
				gr(a, (Y(t), X(() => Y(t).display_name || Y(t).account_name))), gr(m, (Y(t), X(() => Y(t).is_authenticated ? "Reauthenticate" : "Authenticate"))), g = zr(h, 1, "px-4 py-2 bg-white/10 text-[var(--text-primary)] border-none rounded-global transition-colors hover:bg-white/15 active:scale-95", null, g, { active: Y(t).is_active }), Kr(h, "title", (Y(t), X(() => Y(t).is_active ? "Deactivate" : "Activate"))), gr(_, (Y(t), X(() => Y(t).is_active ? "Deactivate" : "Activate")));
			}), Z("click", p, () => ee(Y(t).id)), Z("click", h, () => w(Y(t).id, Y(t).is_active)), Z("click", v, () => C(Y(t).id, Y(t).display_name || Y(t).account_name)), $(e, n);
		}, (e) => {
			$(e, _i());
		}), k(ye), k(me), Cn(() => {
			Kr(re, "type", Y(u) ? "text" : "password"), Kr(re, "placeholder", Y(l) ? "••••••••  (leave blank to keep current)" : "Enter your MusicBrainz Client Secret"), Kr(ie, "title", Y(u) ? "Hide" : "Show"), gr(ae, Y(u) ? "👁️" : "👁️‍🗨️"), oe.disabled = Y(d), gr(se, Y(d) ? "Saving…" : "Save Credentials"), gr(de, Y(f) ? "Expand" : "Collapse"), gr(ge, `Accounts (${(Y(i), X(() => Y(i).length)) ?? ""}/10)`);
		}), Xr(m, () => Y(p), (e) => F(p, e)), Z("click", h, y), Xr(S, () => Y(o), (e) => F(o, e)), Xr(re, () => Y(s), (e) => F(s, e)), Z("click", ie, () => F(u, !Y(u))), Z("click", oe, v), Z("click", ue, () => F(f, !Y(f))), $(e, t);
	};
	Er(ie, (e) => {
		Y(r) ? e(ae) : e(oe, -1);
	}), k(re);
	var se = R(re, 2), ce = (e) => {
		var n = yi(), r = L(n), i = L(r), a = R(L(i), 2);
		k(i);
		var o = R(i, 2), s = L(o), c = R(L(s), 2);
		Wr(c), k(s), Pe(2), k(o);
		var l = R(o, 2), u = L(l), d = R(u, 2), f = L(d, !0);
		k(d), k(l), k(r), k(n), Cn(() => {
			d.disabled = Y(g), gr(f, Y(g) ? "Adding…" : "Add Account");
		}), Z("click", a, x), Xr(c, () => Y(h), (e) => F(h, e)), Z("click", u, x), Z("click", d, S), Z("click", r, $r(function(e) {
			ni.call(this, t, e);
		})), Z("click", n, x), $(e, n);
	};
	return Er(se, (e) => {
		Y(m) && e(ce);
	}), $(e, ne), He(te);
}
customElements.define("musicbrainz-dashboard-card", li(xi, { apiBase: {} }, [], []));
//#endregion
export { xi as default };
